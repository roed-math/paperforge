#!/usr/bin/env python3
"""paperforge review server: an author-facing UI over the decision artifacts.

The pipeline's judgment calls live in committed JSON artifacts (novelty
claims, notation disambiguation, citation needs, formalized-known). This
serves a dashboard where each pending item is a card with its evidence
(every field label carries help hovertext), knowl-style in-place previews of
the paper anchors (typeset with the paper's own macros), status buttons with
documented meanings, and autosaving notes. Decisions write back into the
native artifact files immediately — the same files the pipeline reads.

Run from the instance root:    python3 <paperforge>/review/review_server.py
Stdlib + lxml (already a validator dependency).
"""
from __future__ import annotations

import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
MATHJAX_LOCAL = ROOT / "vendor" / "node_modules" / "mathjax"
MATHJAX_CDN = "https://cdn.jsdelivr.net/npm/mathjax@4/tex-mml-chtml.js"


MJX_FONT_LOCAL = ROOT / "vendor" / "node_modules" / "@mathjax"
FONTPATH_PATCH = (
    '<script>window.MathJax = window.MathJax || {};'
    'window.MathJax.output = Object.assign({}, window.MathJax.output,'
    ' {fontPath: "/mjx-font/%%FONT%%-font"});</script>')


def localize_cdn(html: str) -> str:
    """Point CDN assets at local copies when vendored (fetch-vendor.sh)."""
    if MATHJAX_LOCAL.exists():
        html = html.replace(MATHJAX_CDN, "/mathjax/tex-mml-chtml.js")
        html = html.replace(
            "https://cdn.jsdelivr.net/npm/mathjax@4", "/mathjax")
        if MJX_FONT_LOCAL.exists():
            # the math font is a separate npm package the bundle fetches at
            # runtime; point it at the vendored copy via output.fontPath
            # (attribute order varies: <script defer src=...>)
            html = re.sub(
                r'(<script[^>]*src="/mathjax/tex-mml-chtml\.js")',
                FONTPATH_PATCH + r"\1", html, count=1)
    return html


# ---------------------------------------------------------------- anchors

def _items():
    numbering = ROOT / "crosswalk" / "numbering-current.json"
    if not hasattr(_items, "_c"):
        _items._c = (json.load(open(numbering))["items"]
                     if numbering.exists() else {})
    return _items._c


def tag_page(tag: str) -> str | None:
    """Which output/web page contains this tag (chunk-0 builds put the whole
    document on index.html)."""
    items = _items()
    rec = items.get(tag)
    if rec is None:
        return None
    page = None
    if rec["kind"] in ("section", "appendix"):
        page = f"{tag}.html"
    else:
        sec = rec.get("section")
        for t, r in items.items():
            if r["kind"] in ("section", "appendix") and r["number"] == sec:
                page = f"{t}.html"
                break
    web = ROOT / "output" / "web"
    if page and not (web / page).exists():
        singles = [f.name for f in web.glob("*.html") if f.name != "index.html"]
        if len(singles) == 1:              # chunk-0 build: one document page
            return singles[0]
        if (web / "index.html").exists():
            return "index.html"
    return page


def links_for(tags) -> list[dict]:
    out = []
    for t in tags or []:
        page = tag_page(t)
        if page:
            out.append({"label": t, "tag": t,
                        "href": f"/paper/{page}#{t}"})
    return out


def extract_fragment(tag: str) -> str | None:
    """The anchored element's HTML from the built paper (knowl content)."""
    page = tag_page(tag)
    if page is None:
        return None
    path = ROOT / "output" / "web" / page
    if not path.exists():
        return None
    import lxml.html
    doc = lxml.html.parse(str(path)).getroot()
    el = doc.get_element_by_id(tag, None)
    if el is None:
        return None
    for junk in el.xpath('.//div[@class="autopermalink"]'):
        junk.getparent().remove(junk)
    return lxml.html.tostring(el, encoding="unicode")


def _bib_pdf(text: str, pdfs: list[Path]) -> str | None:
    """Local PDF for a bibliography entry: long-word token overlap with the
    filename, but ONLY if an author surname (a capitalized word from the
    entry's author segment) also appears in the filename — generic title
    words like 'local fields' otherwise cause false matches."""
    toks = {w.lower() for w in re.findall(r"[A-Za-z]{5,}", text)}
    # true author surnames: capitalized word preceded by initials ("B. Kahn"),
    # minus journal-abbreviation artifacts ("Canad. J. Math" -> "Math")
    JUNK = {"math", "pure", "appl", "algebra", "invent", "acad", "nauk",
            "izv", "canad", "proc", "amer", "reine", "angew", "ann", "ser",
            "soc", "trans", "monographs", "press", "springer"}
    surnames = {w.lower() for w in
                re.findall(r"(?:[A-Z]\.\s*)+([A-Z][A-Za-z'\-]{2,})", text)
                } - JUNK
    best, score = None, 0
    for p in pdfs:
        ftoks = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", p.stem)}
        hits = len(surnames & ftoks)
        # a STRICT MAJORITY of the entry's authors must appear in the
        # filename (rules out co-author overlap with a different work)
        if not surnames or hits * 2 <= len(surnames):
            continue
        s = len((toks - surnames) & ftoks) + 3 * hits
        if s > score:
            best, score = p, s
    if best is not None and score >= 4:
        from urllib.parse import quote
        return "/references/" + quote(best.name)
    return None


def collect_bib() -> dict:
    """bib key -> {text, short, pdf}: converted bibliography + extra-biblio +
    new_refs proposed by pending novelty claims; pdf = local copy when one
    matches in references/."""
    raw = {}
    main = ROOT / "source" / "main.ptx"
    if main.exists():
        for m in re.finditer(
                r'<biblio[^>]*xml:id="(bib-[^"]+)"[^>]*>(.*?)</biblio>',
                main.read_text(), re.S):
            raw[m.group(1)] = " ".join(
                re.sub(r"<[^>]+>", " ", m.group(2)).split())
    extra = ROOT / "references" / "extra-biblio.xml"
    if extra.exists():
        for m in re.finditer(
                r'<biblio[^>]*xml:id="(bib-[^"]+)"[^>]*>(.*?)</biblio>',
                extra.read_text(), re.S):
            raw.setdefault(m.group(1), " ".join(
                re.sub(r"<[^>]+>", " ", m.group(2)).split()))
    for path, group in ((ROOT / "novelty" / "claims.json", "claims"),
                        (ROOT / "followups" / "questions.json", "questions")):
        if not path.exists():
            continue
        for c in json.load(open(path))[group].values():
            for k, v in (c.get("new_refs") or {}).items():
                raw.setdefault(k, re.sub(r"\\[a-zA-Z]+|[{}]|<[^>]+>", "",
                                         " ".join(v.split()))
                               + "  [NEW — materializes on approval]")
    pdfs = sorted((ROOT / "references").glob("*.pdf"))
    out = {}
    for k, text in raw.items():
        out[k] = {"text": text,
                  "short": text[:90] + ("…" if len(text) > 90 else ""),
                  "pdf": _bib_pdf(text, pdfs)}
    return out


def extract_macros() -> str:
    """The paper's \\newcommand block (div#latex-macros inner HTML)."""
    web = ROOT / "output" / "web"
    for page in sorted(web.glob("sec-*.html")) or sorted(web.glob("*.html")):
        import lxml.html
        doc = lxml.html.parse(str(page)).getroot()
        el = doc.get_element_by_id("latex-macros", None)
        if el is not None:
            return lxml.html.tostring(el, encoding="unicode")
    return ""


# ---------------------------------------------------------------- adapters
# Adapter contract: items() -> [{id, title, fields:[{label,value,help}],
# text?, text_help?, links, status, choices, choice_help:{}, note}];
# decide(id, status, note, text) writes back. help() -> artifact-level blurb.


def gen_field(rec=None, data=None):
    """Provenance field: item-level 'generator', else artifact-level
    '_generator' (docs/ARCHITECTURE.md, provenance conventions)."""
    g = (rec or {}).get("generator") or (data or {}).get("_generator")
    if not g:
        return None
    return dict(label="proposed by", value=g,
                help="The model/agent that generated this proposal. The "
                     "decision is yours either way; re-runs never overwrite "
                     "decisions, whoever the generator is.")


class Novelty:
    name = "novelty"
    label = "Novelty claims"
    path = ROOT / "novelty" / "claims.json"
    blurb = ("Typed novelty claims for the introduction (docs/NOVELTY.md). "
             "Approved claims — and only approved claims — are rendered into "
             "the intro's novelty exposition by the intro-novelty pass.")
    choices = ["proposed", "author-approved", "author-rejected",
               "needs-discussion"]
    choice_help = {
        "proposed": "Drafted by the pipeline; awaiting your judgment. Not rendered.",
        "author-approved": "You endorse the claim as stated (edit the text first if needed). Will be rendered into the introduction.",
        "author-rejected": "Wrong, overstated, or unwanted. Never rendered; kept for the record so the pipeline does not re-propose it.",
        "needs-discussion": "Parked for a conversation. Neither rendered nor discarded.",
    }
    CLASSES = {1: "novel method", 2: "surprising result",
               3: "weakened hypotheses", 4: "generalizable definition",
               5: "cross-field ingredient"}

    def items(self):
        if not self.path.exists():
            return []
        raw = json.load(open(self.path))
        data = raw["claims"]
        out = []
        for cid, c in data.items():
            fields = [
                dict(label=f"class {c['cls']} — {self.CLASSES.get(c['cls'], '?')}",
                     value="",
                     help="The five novelty classes: 1 novel method / 2 "
                          "surprising result / 3 weakened hypotheses / 4 "
                          "generalizable definition / 5 cross-field "
                          "ingredient. See docs/NOVELTY.md."),
                dict(label="confidence", value=c.get("confidence", "?"),
                     help="The pipeline's confidence in the claim AS STATED "
                          "(after its literature checks). Not your judgment — "
                          "that is the status."),
                dict(label="evidence", value="; ".join(c.get("evidence", [])),
                     help="Pointers into novelty/evidence.json plus the "
                          "recorded literature-search trail (each search: "
                          "query + what was/wasn't found). Judge whether the "
                          "searches were adequate."),
            ]
            if c.get("hedge"):
                fields.append(dict(
                    label="hedge", value=c["hedge"],
                    help="The strongest phrasing the evidence supports. "
                         "Rendered prose must not exceed this hedge."))
            if c.get("new_refs"):
                fields.append(dict(
                    label="new references",
                    value=", ".join(c["new_refs"]),
                    help="Bibliography entries this claim introduces. They "
                         "are added to references/extra-biblio.xml only when "
                         "the claim is approved and rendered — so the "
                         "no-uncited-entries gate stays green meanwhile."))
            if c.get("machine_checkable"):
                fields.append(dict(
                    label="machine-checkable", value="yes",
                    help="The claim's core comparison is formal (e.g. Lean "
                         "hypothesis lists), not judgment."))
            gf = gen_field(c, raw)
            if gf:
                fields.append(gf)
            out.append(dict(
                id=cid, title=cid, fields=fields,
                text=c["statement"],
                text_help="The claim itself, in inline LaTeX: $...$ math "
                          "(the paper's macros work), \\cite[pin]{KEY} "
                          "citations by exact bibliography key (see the "
                          "picker), \\emph, \\texttt, --/--- dashes. "
                          "Rendered into the introduction through the same "
                          "LaTeX->PreTeXt converter as the paper itself.",
                links=links_for(c.get("paper_anchors")),
                status=c["status"], choices=self.choices,
                choice_help=self.choice_help,
                note=c.get("author_note", "")))
        return out

    def decide(self, iid, status, note, text):
        data = json.load(open(self.path))
        c = data["claims"][iid]
        if status:
            c["status"] = status
        if note is not None:
            c["author_note"] = note
        if text is not None:
            c["statement"] = text
        json.dump(data, open(self.path, "w"), indent=1)


class Followups:
    name = "followups"
    label = "Follow-up questions"
    path = ROOT / "followups" / "questions.json"
    blurb = ("Candidate follow-up questions / natural next steps, proposed "
             "by the pipeline from the paper + formalization (skills/"
             "followup-questions). Human questions live in the same file "
             "(distinct generator). Approved questions are eligible for a "
             "closing 'Further questions' section — or the website only.")
    choices = ["proposed", "author-approved", "author-rejected",
               "needs-discussion"]
    choice_help = {
        "proposed": "Drafted by the pipeline; awaiting your judgment. Not rendered.",
        "author-approved": "Worth stating publicly (edit the text first if "
                           "needed). Eligible for the Further-questions "
                           "section or the project website.",
        "author-rejected": "Wrong, uninteresting, or already answered. Kept "
                           "for the record so the pipeline does not "
                           "re-propose it.",
        "needs-discussion": "Parked for a conversation. Neither rendered nor "
                            "discarded.",
    }
    CLASSES = {
        "extension": "same theorem, wider scope",
        "sharpness": "minimality / converses / no-go statements",
        "application": "what the result unlocks downstream",
        "method-export": "the technique applied elsewhere",
        "formalization": "Lean-side continuations and re-verification",
        "data": "databases, tables, machine-readable artifacts",
    }

    def items(self):
        if not self.path.exists():
            return []
        raw = json.load(open(self.path))
        out = []
        for qid, q in raw["questions"].items():
            fields = [
                dict(label=f"class: {q['cls']} — "
                           f"{self.CLASSES.get(q['cls'], '?')}",
                     value="",
                     help="The follow-up taxonomy: extension / sharpness / "
                          "application / method-export / formalization / "
                          "data. One primary class per question."),
                dict(label="confidence", value=q.get("confidence", "?"),
                     help="The pipeline's confidence that the question is "
                          "genuinely open AND naturally posed by this paper. "
                          "Not your judgment — that is the status."),
                dict(label="grounding", value="; ".join(q.get("evidence", [])),
                     help="What in the paper or the formalization seeds this "
                          "question: proof stages, census axioms, hedges, "
                          "scope restrictions, independence remarks."),
            ]
            if q.get("literature"):
                fields.append(dict(
                    label="literature check", value=q["literature"],
                    help="What a literature pass found or still must check. "
                         "A question already answered in print is demoted "
                         "to a citation, never rendered as open."))
            if q.get("new_refs"):
                fields.append(dict(
                    label="new references",
                    value=", ".join(q["new_refs"]),
                    help="Bibliography entries this question introduces. "
                         "Materialized into references/extra-biblio.xml "
                         "only when the question is approved and rendered — "
                         "the no-uncited-entries gate stays green meanwhile."))
            gf = gen_field(q, raw)
            if gf:
                fields.append(gf)
            out.append(dict(
                id=qid, title=qid, fields=fields,
                text=q["statement"],
                text_help="The question itself, in inline LaTeX (same "
                          "conventions as novelty claims): $...$ math with "
                          "the paper's macros, \\cite[pin]{KEY} by exact "
                          "bibliography key, \\cref{label} internal "
                          "references, \\emph, \\texttt, --/---. What you "
                          "approve is what would be typeset.",
                links=links_for(q.get("paper_anchors")),
                status=q["status"], choices=self.choices,
                choice_help=self.choice_help,
                note=q.get("author_note", "")))
        return out

    def decide(self, iid, status, note, text):
        data = json.load(open(self.path))
        q = data["questions"][iid]
        if status:
            q["status"] = status
        if note is not None:
            q["author_note"] = note
        if text is not None:
            q["statement"] = text
        json.dump(data, open(self.path, "w"), indent=1)


class Disambig:
    name = "disambig"
    label = "Notation senses"
    path = ROOT / "notation" / "disambiguation.json"
    map_path = ROOT / "notation" / "notation-map.json"
    blurb = ("Block-grain sense decisions for ambiguous single-letter "
             "notation (docs/NOTATION.md). The chosen sense drives which "
             "hover definition each occurrence of the letter gets in that "
             "block; 'none' leaves the letter unwrapped there.")

    def _senses(self):
        senses, sense_help = {}, {}
        if self.map_path.exists():
            m = json.load(open(self.map_path))
            for k, rec in m.items():
                if rec.get("kind") == "ambiguous":
                    senses[k] = list(rec["senses"]) + ["none"]
                    for sk, sv in rec["senses"].items():
                        plain = re.sub(r"\\\(|\\\)|\\[a-zA-Z]+|[{}]", " ",
                                       sv.get("definition", ""))
                        sense_help[sk] = re.sub(r"\s+", " ", plain).strip()[:200]
        sense_help["none"] = ("Not tracked notation in this block: the "
                              "letter is a local/generic use — no hover, "
                              "no wrap.")
        return senses, sense_help

    def items(self):
        if not self.path.exists():
            return []
        data = json.load(open(self.path))
        senses, sense_help = self._senses()
        gf = gen_field(data=data)
        out = []
        for key, blocks in data.items():
            if key.startswith("_"):        # file metadata, not a letter
                continue
            for block, sense in sorted(blocks.items()):
                fields = [dict(
                    label="block", value=block,
                    help="The theorem-or-division tag this decision "
                         "covers. One sense per block (a statement "
                         "essentially never mixes senses of one letter).")]
                if gf:
                    fields.append(gf)
                out.append(dict(
                    id=f"{key}@{block}", title=f"{key} in {block}",
                    fields=fields,
                    text=None, links=links_for([block]),
                    status=sense, choices=senses.get(key, [sense, "none"]),
                    choice_help=sense_help, note=""))
        return out

    def decide(self, iid, status, note, text):
        key, block = iid.split("@", 1)
        data = json.load(open(self.path))
        if status:
            data[key][block] = status
        json.dump(data, open(self.path, "w"), indent=1)


class CitationNeeds:
    name = "citations"
    label = "Citation needs"
    path = ROOT / "references" / "citation-needs.json"
    blurb = ("Blocks that may state known mathematics without citing it "
             "(docs/REFERENCES.md, citation-audit). Axiom-driven entries come "
             "from the Lean census; named-result entries from the "
             "authority-phrase scan.")
    choices = ["needs-citation", "cited-nearby", "common-knowledge"]
    choice_help = {
        "needs-citation": "A citation must be added at this anchor. The "
                          "pipeline creates/keeps an insertion fragment "
                          "citing the listed works.",
        "cited-nearby": "An existing citation in the same division already "
                        "covers this — no new citation.",
        "common-knowledge": "No citation expected at this paper's level "
                            "(e.g. Hensel's lemma for this audience).",
    }
    FIELD_HELP = {
        "works": "The literature works involved — tokens resolved through "
                 "references/bib-aliases.json to bibliography entries.",
        "fixed_by": "The insertion fragment (content/insertions/) that "
                    "resolves this need at ingest time.",
        "note": "The pipeline's reasoning for its classification.",
        "decision": "",
    }

    def items(self):
        if not self.path.exists():
            return []
        data = json.load(open(self.path))
        out = []
        for group in ("axiom-driven", "named-results"):
            for iid, rec in data.get(group, {}).items():
                fields = [dict(label=k,
                               value=v if isinstance(v, str) else json.dumps(v),
                               help=self.FIELD_HELP.get(k,
                                    "Pipeline metadata."))
                          for k, v in rec.items()
                          if k not in ("decision", "author_note", "generator")]
                fields.insert(0, dict(
                    label="source", value=group,
                    help="axiom-driven: the Lean census anchors this fact "
                         "here. named-results: the authority-phrase scan "
                         "flagged the block."))
                gf = gen_field(rec, data)
                if gf:
                    fields.append(gf)
                tag = iid.split("#")[0]
                out.append(dict(
                    id=f"{group}|{iid}", title=iid, fields=fields,
                    text=None, links=links_for([tag]),
                    status=rec.get("decision", "?"), choices=self.choices,
                    choice_help=self.choice_help,
                    note=rec.get("author_note", "")))
        return out

    def decide(self, iid, status, note, text):
        group, key = iid.split("|", 1)
        data = json.load(open(self.path))
        rec = data[group][key]
        if status:
            rec["decision"] = status
        if note is not None:
            rec["author_note"] = note
        json.dump(data, open(self.path, "w"), indent=1)


class Known:
    name = "known"
    label = "Formalized-known"
    path = ROOT / "references" / "formalized-known.json"
    blurb = ("Classification of formalization nodes as known mathematics vs "
             "the paper's contribution (docs/REFERENCES.md, citable-node "
             "funnel). 'Known' nodes should be cited, and their paper "
             "counterparts are compression candidates.")
    choices = ["known", "known-definition", "known-variant", "novel",
               "uncertain"]
    choice_help = {
        "known": "Matches a specific literature statement (see citation).",
        "known-definition": "A standard notion; this node is its encoding.",
        "known-variant": "Close to a literature statement but with a real "
                         "delta (weaker hypotheses, one-sidedness, ...) — "
                         "check the comparison is fair.",
        "novel": "The paper's own contribution — not citable as prior work.",
        "uncertain": "The pipeline could not decide; needs your read.",
    }
    FIELD_HELP = {
        "citation": "Best literature match the pipeline found (the claim "
                    "this classification rests on).",
        "works": "Work tokens, resolved via references/bib-aliases.json.",
        "paper_status": "What this means for the paper: already cited / "
                        "suggest citation / census-covered / "
                        "formalization-side only.",
        "confidence": "The pipeline's confidence in the match.",
        "note": "Caveats — including explicit requests for your review.",
        "machine_checkable": "The comparison is formal (Lean hypothesis "
                             "lists), not judgment.",
    }

    def items(self):
        if not self.path.exists():
            return []
        raw = json.load(open(self.path))
        data = raw["decisions"]
        out = []
        for decl, rec in data.items():
            fields = [dict(label=k,
                           value=v if isinstance(v, str) else json.dumps(v),
                           help=self.FIELD_HELP.get(k, "Pipeline metadata."))
                      for k, v in rec.items()
                      if k not in ("status", "author_note", "generator")]
            gf = gen_field(rec, raw)
            if gf:
                fields.append(gf)
            out.append(dict(id=decl, title=decl.split(".")[-1], fields=fields,
                            text=None, links=[], status=rec["status"],
                            choices=self.choices, choice_help=self.choice_help,
                            note=rec.get("author_note", "")))
        return out

    def decide(self, iid, status, note, text):
        data = json.load(open(self.path))
        rec = data["decisions"][iid]
        if status:
            rec["status"] = status
        if note is not None:
            rec["author_note"] = note
        json.dump(data, open(self.path, "w"), indent=1)


class Marks:
    """Author intents captured by clicking in the paper (paper-marks.js).

    Each mark is a worklist item for a specific pass: notation-link requests
    feed the notation map, reference marks feed citation-audit, detail marks
    feed the detail-retier passes. A pass that acts on a mark flips it to
    'applied' (with a note saying what was done)."""
    name = "marks"
    label = "Review marks"
    path = ROOT / "directives" / "marks.json"
    blurb = ("Click-registered author intents from reading the paper "
             "(select a pen mode in the margin palette, then click). Open "
             "marks are the worklist; passes flip them to applied.")
    choices = ["open", "applied", "dismissed"]
    choice_help = {
        "open": "Registered and waiting for the corresponding pass.",
        "applied": "The requested change has been made (see the note).",
        "dismissed": "Withdrawn — no change wanted after all.",
    }
    MODE_HELP = {
        "notation": "This term/symbol should get a ? hover definition "
                    "(feeds notation/notation-map.json curation).",
        "reference": "A citation should be added here (feeds the "
                     "citation-audit worklist).",
        "detail-high": "Too much detail here — move prose down to a higher "
                       "detail level (collapsed by default).",
        "detail-low": "Too little detail here — add more explanation "
                      "(at a higher detail level or inline).",
    }

    def _load(self):
        if self.path.exists():
            return json.load(open(self.path))
        return {"_comment": "Click-registered review marks (paper-marks.js; "
                            "review dashboard 'Review marks' tab). Statuses: "
                            "open | applied | dismissed.",
                "marks": {}}

    def add(self, rec: dict) -> str:
        data = self._load()
        mid = f"mk-{len(data['marks']) + 1:03d}"
        while mid in data["marks"]:
            mid = f"mk-{int(mid[3:]) + 1:03d}"
        data["marks"][mid] = {
            "mode": rec.get("mode", "?"),
            "text": (rec.get("text") or "")[:200],
            "context": (rec.get("context") or "")[:300],
            "anchor": rec.get("anchor", ""),
            "block": rec.get("block", ""),
            "page": rec.get("page", ""),
            "created": __import__("datetime").date.today().isoformat(),
            "status": "open",
            "author_note": "",
            "generator": "roed",
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        json.dump(data, open(self.path, "w"), indent=1)
        return mid

    def open_marks(self, page: str | None = None) -> list[dict]:
        data = self._load()
        return [dict(id=k, **v) for k, v in data["marks"].items()
                if v["status"] == "open" and (not page or v["page"] == page)]

    def items(self):
        data = self._load()
        out = []
        for mid, m in data["marks"].items():
            fields = [
                dict(label=f"mode: {m['mode']}", value="",
                     help=self.MODE_HELP.get(m["mode"], "Review mark.")),
                dict(label="context", value=m.get("context", ""),
                     help="The surrounding sentence at the click site."),
                dict(label="where", value=m.get("anchor", ""),
                     help="The nearest anchored element at the click site."),
            ]
            gf = gen_field(m, data)
            if gf:
                fields.append(gf)
            block = m.get("block") or m.get("anchor")
            out.append(dict(
                id=mid, title=f"{m['mode']}: {m.get('text') or '(no text)'}",
                fields=fields,
                text=m.get("text"),
                text_help="The clicked term/selection. Edit if the click "
                          "captured the wrong span.",
                links=links_for([block] if block else []),
                status=m["status"], choices=self.choices,
                choice_help=self.choice_help,
                note=m.get("author_note", "")))
        return out

    def decide(self, iid, status, note, text):
        data = self._load()
        m = data["marks"][iid]
        if status:
            m["status"] = status
        if note is not None:
            m["author_note"] = note
        if text is not None:
            m["text"] = text
        json.dump(data, open(self.path, "w"), indent=1)


ADAPTERS = {a.name: a() for a in (Novelty, Followups, Disambig,
                                  CitationNeeds, Known, Marks)}


# ---------------------------------------------------------------- server

class Handler(SimpleHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/review"):
            html = localize_cdn(
                (HERE / "dashboard.html").read_text()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if url.path == "/api/artifacts":
            return self._json([{"name": a.name, "label": a.label,
                                "blurb": a.blurb, "count": len(a.items())}
                               for a in ADAPTERS.values()])
        if url.path == "/api/items":
            q = parse_qs(url.query)
            a = ADAPTERS.get(q.get("artifact", [""])[0])
            if a:
                return self._json(a.items())
            return self._json({"error": "unknown artifact"}, 400)
        if url.path == "/api/margin":
            q = parse_qs(url.query)
            page = q.get("page", [""])[0]
            out = []
            for a in ADAPTERS.values():
                for it in a.items():
                    anchors = [l["tag"] for l in it.get("links", [])
                               if tag_page(l["tag"]) == page]
                    if not anchors:
                        continue
                    out.append({
                        "artifact": a.name, "artifact_label": a.label,
                        "id": it["id"], "title": it["title"],
                        "status": it["status"], "choices": it["choices"],
                        "choice_help": it.get("choice_help", {}),
                        "note": it.get("note", ""),
                        "text": it.get("text"),
                        "summary": "; ".join(
                            f"{f['label']}: {f['value']}" if f.get("value")
                            else f["label"]
                            for f in it.get("fields", [])[:3]),
                        "anchors": anchors,
                    })
            return self._json(out)
        if url.path == "/api/tags":
            out = {}
            for tag, r in _items().items():
                rec = {"tag": tag, "kind": r["kind"], "number": r["number"]}
                out[tag] = rec
                if r.get("label"):
                    out[r["label"]] = rec
            return self._json(out)
        if url.path == "/api/bib":
            return self._json(collect_bib())
        if url.path == "/api/macros":
            return self._json({"html": extract_macros()})
        if url.path == "/api/fragment":
            q = parse_qs(url.query)
            tag = q.get("tag", [""])[0]
            frag = extract_fragment(tag)
            if frag is None:
                return self._json({"error": f"no fragment for {tag}"}, 404)
            return self._json({"html": frag})
        if url.path == "/review-paper-margin.js":
            body = (HERE / "paper-margin.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == "/review-paper-tags.js":
            body = (HERE / "paper-tags.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == "/review-paper-marks.js":
            body = (HERE / "paper-marks.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == "/api/marks":
            q = parse_qs(url.query)
            page = q.get("page", [None])[0]
            return self._json(ADAPTERS["marks"].open_marks(page))
        if url.path.startswith("/mjx-font/") and MJX_FONT_LOCAL.exists():
            rest = self.path[len("/mjx-font/"):]
            # the bundle appends @version to the package segment; the
            # vendored directory has no version suffix
            rest = re.sub(r"^([^/]+?)@[^/]+", r"\1", rest)
            self.path = "/vendor/node_modules/@mathjax/" + rest
            return super().do_GET()
        if url.path.startswith("/mathjax/") and MATHJAX_LOCAL.exists():
            rest = self.path[len("/mathjax/"):]
            target = MATHJAX_LOCAL / rest
            if rest.endswith(".js") and MJX_FONT_LOCAL.exists() \
                    and target.exists():
                # rewrite the bundle's default CDN font base to the local
                # mount (PreTeXt configures MathJax via a startup module, so
                # an inline config patch cannot override it there)
                body = target.read_text(errors="ignore").replace(
                    "https://cdn.jsdelivr.net/npm/@mathjax",
                    "/mjx-font").encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.path = "/vendor/node_modules/mathjax/" + rest
            return super().do_GET()
        if url.path.startswith("/lean/"):
            # local mirror of the site's /lean/ (doc-gen4 subsets), so the
            # paper's Lean badges resolve during review too
            self.path = "/output/leandocs/" + url.path[len("/lean/"):]
            return super().do_GET()
        if url.path.startswith("/paper/"):
            rel = url.path[len("/paper/"):] or "index.html"
            target = ROOT / "output" / "web" / rel
            if target.suffix == ".html" and target.exists():
                # review mode: inject the tag-discovery layer (the standalone
                # build in output/web is untouched)
                html = localize_cdn(target.read_text(errors="ignore")).replace(
                    "</body>",
                    '<script src="/review-paper-tags.js"></script>'
                    '<script src="/review-paper-margin.js"></script>'
                    '<script src="/review-paper-marks.js"></script></body>', 1)
                body = html.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.path = "/output/web/" + rel
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        if self.path == "/api/mark":
            mid = ADAPTERS["marks"].add(req)
            return self._json({"ok": True, "id": mid})
        if self.path != "/api/decide":
            return self._json({"error": "unknown endpoint"}, 404)
        a = ADAPTERS.get(req.get("artifact"))
        if not a:
            return self._json({"error": "unknown artifact"}, 400)
        try:
            a.decide(req["id"], req.get("status"), req.get("note"),
                     req.get("text"))
        except KeyError as e:
            return self._json({"error": f"unknown item {e}"}, 400)
        return self._json({"ok": True})

    def log_message(self, *a):  # quiet
        pass


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                     partial(Handler, directory=str(ROOT)))
    except OSError as e:
        if e.errno != 48:               # EADDRINUSE
            raise
        # is the occupant one of ours? then just point at it
        import urllib.request
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{args.port}/api/artifacts",
                    timeout=2) as r:
                if r.status == 200:
                    print(f"review server already running: "
                          f"http://127.0.0.1:{args.port}/review")
                    print("(kill it with:  lsof -ti tcp:%d | xargs kill)"
                          % args.port)
                    return 0
        except Exception:
            pass
        print(f"port {args.port} is taken by something else — "
              f"try:  --port {args.port + 1}")
        return 1
    print(f"paperforge review: http://127.0.0.1:{args.port}/review")
    print(f"instance: {ROOT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

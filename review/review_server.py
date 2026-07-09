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


# ---------------------------------------------------------------- anchors

def _items():
    numbering = ROOT / "crosswalk" / "numbering-current.json"
    if not hasattr(_items, "_c"):
        _items._c = (json.load(open(numbering))["items"]
                     if numbering.exists() else {})
    return _items._c


def tag_page(tag: str) -> str | None:
    """Which output/web page contains this tag."""
    items = _items()
    rec = items.get(tag)
    if rec is None:
        return None
    if rec["kind"] in ("section", "appendix"):
        return f"{tag}.html"
    sec = rec.get("section")
    for t, r in items.items():
        if r["kind"] in ("section", "appendix") and r["number"] == sec:
            return f"{t}.html"
    return None


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
        data = json.load(open(self.path))["claims"]
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
            if c.get("machine_checkable"):
                fields.append(dict(
                    label="machine-checkable", value="yes",
                    help="The claim's core comparison is formal (e.g. Lean "
                         "hypothesis lists), not judgment."))
            out.append(dict(
                id=cid, title=cid, fields=fields,
                text=c["statement"],
                text_help="The claim itself. Edit freely — the approved text "
                          "is exactly what the intro pass renders from.",
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
        out = []
        for key, blocks in data.items():
            for block, sense in sorted(blocks.items()):
                out.append(dict(
                    id=f"{key}@{block}", title=f"{key} in {block}",
                    fields=[dict(
                        label="block", value=block,
                        help="The theorem-or-division tag this decision "
                             "covers. One sense per block (a statement "
                             "essentially never mixes senses of one letter).")],
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
                          if k not in ("decision", "author_note")]
                fields.insert(0, dict(
                    label="source", value=group,
                    help="axiom-driven: the Lean census anchors this fact "
                         "here. named-results: the authority-phrase scan "
                         "flagged the block."))
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
        data = json.load(open(self.path))["decisions"]
        out = []
        for decl, rec in data.items():
            fields = [dict(label=k,
                           value=v if isinstance(v, str) else json.dumps(v),
                           help=self.FIELD_HELP.get(k, "Pipeline metadata."))
                      for k, v in rec.items()
                      if k not in ("status", "author_note")]
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


ADAPTERS = {a.name: a() for a in (Novelty, Disambig, CitationNeeds, Known)}


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
            html = (HERE / "dashboard.html").read_bytes()
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
        if url.path == "/api/macros":
            return self._json({"html": extract_macros()})
        if url.path == "/api/fragment":
            q = parse_qs(url.query)
            tag = q.get("tag", [""])[0]
            frag = extract_fragment(tag)
            if frag is None:
                return self._json({"error": f"no fragment for {tag}"}, 404)
            return self._json({"html": frag})
        if url.path.startswith("/paper/"):
            self.path = "/output/web/" + self.path[len("/paper/"):]
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/decide":
            return self._json({"error": "unknown endpoint"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
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
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 partial(Handler, directory=str(ROOT)))
    print(f"paperforge review: http://127.0.0.1:{port}/review")
    print(f"instance: {ROOT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

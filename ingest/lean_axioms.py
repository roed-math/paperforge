#!/usr/bin/env python3
"""lean_axioms: extract the formalization's axiom census with citations.

Scans the Lean repo for `axiom` declarations and parses their docstrings for
the citation discipline used in gq2-lean:

    **[Classical — B4.]** ...
    Citation: NSW [1], Ch. VII §7.5, Theorem (7.5.11)(ii) ...; Labute [2], Theorem 8 ...
    Paper: Lemma 3.4 → Prop. 1.1.   (v-snapshot numbering)

Emits ``crosswalk/axiom-citations.json``:

    { "GQ2.Foundations.absGalQ2_maxProTwo_presentation": {
        "census": "B4", "file": "...", "line": N,
        "citation_lines": ["NSW [1], Ch. VII ...", ...],
        "works": ["NSW", "Labute", "Serre"],          # surname/acronym tokens
        "paper_refs": ["Lemma 3.4", "Prop. 1.1"],
        "paper_tags": ["lem-tamestructure", "prop-markedDem"] } , ... }

Also seeds ``references/bib-aliases.json`` (work token -> bib key) for any
token that fuzzy-matches a bibliography entry — author-correctable afterward.
The references validator consumes both.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CENSUS = re.compile(r"\*\*\[Classical\s*[—–-]\s*([A-Z]\d+[′']?)")
CITE_LINE = re.compile(r"Citation[^:\n]{0,40}:\s*(.+?)(?:\n\n|-/|\nPaper:|$)", re.S)
PAPER_LINE = re.compile(r"Paper:\s*(.+?)(?:\n|-/|$)")
PAPER_REF = re.compile(
    r"(Theorem|Thm|Lemma|Lem|Proposition|Prop|Corollary|Cor|Definition|Remark)"
    r"\.?~? ?(\d+\.\d+|[AB]\.\d+)|(?<!§)§(\d+(?:\.\d+)?)|eq\.? ?\((\d+)\)", re.I)
# Work tokens: bracketed-index style "NSW [1]" or "Labute [2]", plus bare
# surnames/acronyms at the start of a citation clause.
# names may be separated from their [index] by a short title chunk
# ("Serre, Local Fields [7]"), and indices may be non-numeric ([CiA]).
WORK = re.compile(r"\b([A-Z][A-Za-z'’\-]+(?:–[A-Z][A-Za-z'’\-]+)*)"
                  r"(?:,[^;\[\]]{0,50}?)?\s*\[\w{1,4}\]"
                  r"|(?:^|;|\+)\s*([A-Z][A-Za-z'’\-]{2,}|[A-Z]{2,4})\b[ ,*]")


def resolve_paper_tags(paper_refs, old_map, cur_items):
    declmap = None
    tags = []
    kindmap = {"theorem": "theorem", "thm": "theorem", "lemma": "lemma",
               "lem": "lemma", "proposition": "proposition", "prop": "proposition",
               "corollary": "corollary", "cor": "corollary",
               "definition": "definition", "remark": "remark"}
    res = {}
    if old_map:
        for label, rec in old_map.items():
            tag = re.sub(r"[:_]", "-", label)
            res.setdefault((rec["old_kind"], rec["old"]), tag)
            res.setdefault(("any", rec["old"]), tag)
    eqmap = {}
    for tag, r in cur_items.items():
        if r["kind"] in kindmap.values():
            res.setdefault((r["kind"], r["number"]), tag)
            res.setdefault(("any", r["number"]), tag)
        elif r["kind"] in ("equation", "align-row"):
            eqmap[r["number"].strip("()")] = tag
    secmap = {}
    for tag, r in cur_items.items():
        if r["kind"] in ("section", "appendix", "subsection"):
            secmap[r["number"]] = tag
    for kind_raw, num, sec, eq in paper_refs:
        if eq:
            if eq in eqmap:
                tags.append(eqmap[eq])
        elif sec:
            if sec in secmap:
                tags.append(secmap[sec])
        elif num:
            kind = kindmap.get(kind_raw.lower(), "any") if kind_raw else "any"
            t = res.get((kind, num)) or res.get(("any", num))
            if t:
                tags.append(t)
    return sorted(set(tags))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lean_root", type=Path)
    ap.add_argument("--current", type=Path, required=True)
    ap.add_argument("--old", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed-aliases", type=Path,
                    help="bibliography-bearing ptx (e.g. source/main.ptx); "
                         "seeds references/bib-aliases.json next to --out")
    ap.add_argument("--aliases-out", type=Path)
    args = ap.parse_args()

    cur = json.load(open(args.current))["items"]
    old = json.load(open(args.old)) if args.old and args.old.exists() else None

    out = {}
    # dedicated pass: `axiom` is not in lean_declmap's DECL keyword list
    AX = re.compile(r"^\s*(?:protected\s+|private\s+)?axiom\s+([A-Za-z_][\w'.]*)")
    for f in sorted(args.lean_root.rglob("*.lean")):
        if ".lake" in f.parts:
            continue
        lines = f.read_text(errors="ignore").splitlines()
        stack, pending, depth = [], None, 0
        NS = re.compile(r"^\s*namespace\s+([A-Za-z_][\w'.]*)")
        SEC = re.compile(r"^\s*section\b")
        END = re.compile(r"^\s*end\b")
        for ln, line in enumerate(lines, 1):
            if depth > 0:
                if pending is not None:
                    pending += "\n" + line
                depth += line.count("/-") - line.count("-/")
                continue
            if "/-" in line:
                if "/--" in line:
                    pending = line[line.index("/--"):]
                depth = line.count("/-") - line.count("-/")
                if depth > 0:
                    continue
                line = line[:line.index("/-")]   # keyword part before comment
            if m := NS.match(line):
                stack.append(m.group(1)); continue
            if SEC.match(line):
                stack.append(""); continue
            if END.match(line) and stack:
                stack.pop(); continue
            if m := AX.match(line):
                ns = [s for s in stack if s]
                full = ".".join(ns + [m.group(1)]) if ns else m.group(1)
                doc = pending or ""
                census = (CENSUS.search(doc) or [None, None])[1]
                cites = [c.strip().replace("\n", " ")
                         for c in CITE_LINE.findall(doc.replace("*", "").replace("`", ""))]
                works = sorted({g1 or g2 for g1, g2 in WORK.findall(" ".join(cites))
                                if (g1 or g2) not in (
                                    "Ch", "Chap", "Thm", "Theorem", "Original",
                                    "Invent", "Math", "Prop", "Proposition",
                                    "See", "Paper", "Definition", "Fields",
                                    "Local", "Cor", "Rem", "Grundlehren")})
                prefs = PAPER_REF.findall(" ".join(PAPER_LINE.findall(doc)))
                out[full] = {
                    "census": census, "file": str(f.relative_to(args.lean_root)),
                    "line": ln, "citation_lines": cites, "works": works,
                    "paper_tags": resolve_paper_tags(prefs, old, cur),
                }
                pending = None
            elif line.strip() and not line.lstrip().startswith("--"):
                if depth == 0:
                    pending = None

    args.out.write_text(json.dumps(out, indent=1))
    ncite = sum(1 for a in out.values() if a["works"])
    print(f"wrote {args.out}: {len(out)} axioms, {ncite} with parsed citations")

    if args.seed_aliases and args.aliases_out:
        bib = re.findall(r'xml:id="bib-([^"]+)"', args.seed_aliases.read_text())
        aliases = {}
        alltok = {w for a in out.values() for w in a["works"]}
        for tok in sorted(alltok):
            hit = [b for b in bib if tok.lower() in b.lower()
                   or b.lower() in tok.lower()]
            aliases[tok] = hit[0] and f"bib-{hit[0]}" if hit else None
        if args.aliases_out.exists():
            existing = json.load(open(args.aliases_out))
            for k, v in aliases.items():
                existing.setdefault(k, v)
            aliases = existing
        args.aliases_out.write_text(json.dumps(aliases, indent=1, sort_keys=True))
        unmapped = [k for k, v in aliases.items() if not v]
        print(f"aliases: {args.aliases_out} ({len(aliases)} tokens, "
              f"{len(unmapped)} unmapped: {unmapped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

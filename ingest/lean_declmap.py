#!/usr/bin/env python3
"""lean_declmap: recover the paper-statement -> Lean-declaration map.

Two high-confidence signals in a formalization repo:
  1. decl names encoding a citation:  prop_8_9, thm_4_2, lemma_6_1 ...
  2. docstrings opening with a bold citation: /-- **Proposition 8.9 ...** -/

Both give (kind, number) citations in the SNAPSHOT numbering the formalization
tracked; resolve them to stable tags via the crosswalk maps and emit

    { tag: [ {"decl": fully.qualified.name, "via": "name|docstring",
              "file": "...", "line": N}, ... ] }

Review the output before feeding it to tex2ptx --lean-map: signal 2 especially
can pick up helper declarations that merely *discuss* a statement.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

KIND = {"theorem": "theorem", "thm": "theorem", "lemma": "lemma", "lem": "lemma",
        "proposition": "proposition", "prop": "proposition",
        "corollary": "corollary", "cor": "corollary", "remark": "remark",
        "definition": "definition", "claim": "claim"}
DECL = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)*"
    r"((?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|partial\s+)*)"
    r"(theorem|lemma|def|abbrev|instance|structure)\s+([A-Za-z_][\w'.]*)")
NS = re.compile(r"^\s*namespace\s+([A-Za-z_][\w'.]*)")
SECTION = re.compile(r"^\s*section\b")
END = re.compile(r"^\s*end\b")
NAME_CITE = re.compile(r"(?:^|_)(thm|prop|lem|lemma|cor)_?(\d+)_(\d+)(?:$|_)")
DOC_CITE = re.compile(
    r"\*\*(Theorem|Thm|Lemma|Lem|Proposition|Prop|Corollary|Cor)\.?~? ?"
    r"(\d+\.\d+|[AB]\.\d+)")
# The GPT formalization's discipline: docstrings cite "manuscript Lemma 2.2"
# (current numbering) or the label itself in backticks: `thm:main`.
MS_CITE = re.compile(
    r"(?:manuscript|paper)\s+(Theorem|Lemma|Proposition|Corollary|Remark|"
    r"Definition|Claim)\s+(\d+\.\d+|[AB]\.\d+)", re.I)
LABEL_CITE = re.compile(
    r"`((?:thm|lem|prop|cor|rem|def|claim|eq)[:][A-Za-z0-9:_-]+)`")


def iter_decls(lean_root: Path):
    """Yield (fully_qualified_name, docstring_or_None, file, lineno, private,
    kind) for every top-level declaration under lean_root. Tracks namespaces,
    anonymous `section` scopes, and skips keyword matches inside block
    comments. `private` matters downstream because doc-gen4 emits no doc
    page for private declarations; `kind` is the declaring keyword
    (theorem/lemma/def/abbrev/instance/structure)."""
    for f in sorted(lean_root.rglob("*.lean")):
        if ".lake" in f.parts:
            continue
        stack: list[str] = []
        pending_doc: str | None = None
        comment_depth = 0
        for ln, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            if comment_depth > 0:
                if pending_doc is not None and len(pending_doc) < 600:
                    pending_doc += " " + line.strip()
                comment_depth += line.count("/-") - line.count("-/")
                continue
            if "/--" in line or "/-!" in line or "/-" in line:
                if "/--" in line:
                    pending_doc = line[line.index("/--"):]
                comment_depth = line.count("/-") - line.count("-/")
                if comment_depth > 0:
                    continue
                line = line[:line.index("/-")]  # keyword part before comment
            if m := NS.match(line):
                stack.append(m.group(1))
                continue
            if SECTION.match(line):
                stack.append("")          # anonymous scope sentinel
                continue
            if END.match(line) and stack:
                stack.pop()
                continue
            if m := DECL.match(line):
                name = m.group(3)
                ns = [s for s in stack if s]
                full = ".".join(ns + [name]) if ns else name
                yield (full, pending_doc, f, ln, "private" in m.group(1),
                       m.group(2))
                pending_doc = None


def load_tag_maps(current_json: Path, old_json: Path | None):
    cur = json.load(open(current_json))["items"]
    res = {}
    labels = {}
    if old_json and old_json.exists():
        for label, rec in json.load(open(old_json)).items():
            tag = re.sub(r"[:_]", "-", label)
            res.setdefault((rec["old_kind"], rec["old"]), tag)
            res.setdefault(("any", rec["old"]), tag)
    for tag, r in cur.items():
        if r.get("label"):
            labels[r["label"]] = tag
        if r["kind"] in KIND.values():
            res.setdefault((r["kind"], r["number"]), tag)
            res.setdefault(("any", r["number"]), tag)
    return res, labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lean_root", type=Path)
    ap.add_argument("--current", type=Path, required=True)
    ap.add_argument("--old", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cite-styles", default="name,docstring",
                    help="comma list of citation disciplines to mine: "
                         "name (prop_8_9), docstring (**Lemma 2.2), "
                         "label (`thm:main`), manuscript ('manuscript "
                         "Lemma 2.2'). label/manuscript suit the GPT "
                         "formalization; on a repo with its own ** "
                         "discipline they over-collect support lemmas.")
    ap.add_argument("--exclude", action="append", default=[],
                    metavar="GLOB",
                    help="skip files matching this root-relative glob "
                         "(repeatable) — e.g. vendored copies of another "
                         "formalization")
    args = ap.parse_args()
    styles = {s.strip() for s in args.cite_styles.split(",") if s.strip()}

    tags, labels = load_tag_maps(args.current, args.old)
    out: dict[str, list] = {}

    def add_tag(tag, cited, decl, via, f, ln, private, kind, flagged):
        rec = {"decl": decl, "via": via, "file": str(f), "line": ln,
               "cited": cited, "kind": kind}
        if flagged:
            # docstring opens with a bold citation: the author of the
            # formalization marked this as THE statement (badge pickers
            # prefer these when a cap limits badges per statement)
            rec["flagged"] = True
        if private:
            # doc-gen4 emits no page for private decls: badge consumers
            # must not link into the docs (tex2ptx renders these unlinked)
            rec["private"] = True
        lst = out.setdefault(tag, [])
        if not any(r["decl"] == decl for r in lst):
            lst.append(rec)

    def add(kind_num, num, decl, via, f, ln, private, kind, flagged):
        tag = tags.get((kind_num, num)) or tags.get(("any", num))
        if tag:
            add_tag(tag, f"{kind_num} {num}", decl, via, f, ln, private,
                    kind, flagged)

    from fnmatch import fnmatch
    for full, pending_doc, f, ln, private, kind in iter_decls(args.lean_root):
        name = full.rsplit(".", 1)[-1]
        rel = f.relative_to(args.lean_root)
        if any(fnmatch(str(rel), g) for g in args.exclude):
            continue
        head = (pending_doc or "")[:300]
        flagged = head.startswith("/-- **")
        if "name" in styles and (nm := NAME_CITE.search(name)):
            add(KIND[nm.group(1)], f"{nm.group(2)}.{nm.group(3)}",
                full, "name", rel, ln, private, kind, flagged)
        if not pending_doc:
            continue
        if "docstring" in styles and (dm := DOC_CITE.search(head[:200])):
            add(KIND[dm.group(1).lower()], dm.group(2), full,
                "docstring", rel, ln, private, kind, flagged)
        # the manuscript-phrase and backtick-label disciplines (the GPT
        # formalization). Statements are trusted; supporting defs count
        # only when the docstring opens with a bold flagged citation —
        # otherwise passing mentions ("the Lean form of Lemma 2.1 ...")
        # would badge every helper.
        strong = kind in ("theorem", "lemma") or flagged
        if not strong:
            continue
        if "label" in styles and (lm := LABEL_CITE.search(head)):
            tag = labels.get(lm.group(1))
            if tag:
                add_tag(tag, lm.group(1), full, "label", rel, ln, private,
                        kind, flagged)
                continue
        if "manuscript" in styles and (mm := MS_CITE.search(head)):
            add(KIND[mm.group(1).lower()], mm.group(2), full,
                "manuscript", rel, ln, private, kind, flagged)
    args.out.write_text(json.dumps(out, indent=1))
    n = sum(len(v) for v in out.values())
    print(f"wrote {args.out}: {len(out)} tags, {n} decl links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

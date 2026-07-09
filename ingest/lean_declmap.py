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
    r"(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|partial\s+)*"
    r"(theorem|lemma|def|abbrev|instance|structure)\s+([A-Za-z_][\w'.]*)")
NS = re.compile(r"^\s*namespace\s+([A-Za-z_][\w'.]*)")
SECTION = re.compile(r"^\s*section\b")
END = re.compile(r"^\s*end\b")
NAME_CITE = re.compile(r"(?:^|_)(thm|prop|lem|lemma|cor)_?(\d+)_(\d+)(?:$|_)")
DOC_CITE = re.compile(
    r"\*\*(Theorem|Thm|Lemma|Lem|Proposition|Prop|Corollary|Cor)\.?~? ?"
    r"(\d+\.\d+|[AB]\.\d+)")


def iter_decls(lean_root: Path):
    """Yield (fully_qualified_name, docstring_or_None, file, lineno) for every
    top-level declaration under lean_root. Tracks namespaces, anonymous
    `section` scopes, and skips keyword matches inside block comments."""
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
                name = m.group(2)
                ns = [s for s in stack if s]
                full = ".".join(ns + [name]) if ns else name
                yield full, pending_doc, f, ln
                pending_doc = None


def load_tag_maps(current_json: Path, old_json: Path | None):
    cur = json.load(open(current_json))["items"]
    res = {}
    if old_json and old_json.exists():
        for label, rec in json.load(open(old_json)).items():
            tag = re.sub(r"[:_]", "-", label)
            res.setdefault((rec["old_kind"], rec["old"]), tag)
            res.setdefault(("any", rec["old"]), tag)
    for tag, r in cur.items():
        if r["kind"] in KIND.values():
            res.setdefault((r["kind"], r["number"]), tag)
            res.setdefault(("any", r["number"]), tag)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lean_root", type=Path)
    ap.add_argument("--current", type=Path, required=True)
    ap.add_argument("--old", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    tags = load_tag_maps(args.current, args.old)
    out: dict[str, list] = {}

    def add(kind, num, decl, via, f, ln):
        tag = tags.get((kind, num)) or tags.get(("any", num))
        if not tag:
            return
        rec = {"decl": decl, "via": via, "file": str(f), "line": ln,
               "cited": f"{kind} {num}"}
        lst = out.setdefault(tag, [])
        if not any(r["decl"] == decl for r in lst):
            lst.append(rec)

    for full, pending_doc, f, ln in iter_decls(args.lean_root):
        name = full.rsplit(".", 1)[-1]
        if nm := NAME_CITE.search(name):
            add(KIND[nm.group(1)], f"{nm.group(2)}.{nm.group(3)}",
                full, "name", f.relative_to(args.lean_root), ln)
        if pending_doc:
            dm = DOC_CITE.search(pending_doc[:200])
            if dm:
                add(KIND[dm.group(1).lower()], dm.group(2), full,
                    "docstring", f.relative_to(args.lean_root), ln)
    args.out.write_text(json.dumps(out, indent=1))
    n = sum(len(v) for v in out.values())
    print(f"wrote {args.out}: {len(out)} tags, {n} decl links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate the trust-base table of the intro's formalization subsection.

Joins the live axiom census (extracted from the primary formalization by
ingest/lean_axioms.py) with the hand-authored row annotations, and rewrites
the block between the trust-table:begin/end markers of the target insertion.
Paths and the badge project come from paper.toml [trust_table]:

    [trust_table]
    project = "my-lean"                       # <lean project="..."> on each row
    target = "content/insertions/62-....ptx"  # carries the marker block
    annotations = "references/trust-annotations.json"
    census = "crosswalk/axiom-citations.json"

Drift gates (make CI fail if the paper's table and the Lean axiom census
diverge):
  * the annotation keys and the census axiom set must agree exactly
    (same declarations, same count) — hard error otherwise;
  * --check mode additionally fails if the insertion file's generated block
    is stale.  `paperforge build web` runs the generator before ingest and
    the check after the census refresh, so a census change fails the build
    until the table is regenerated.

An instance without a [trust_table] section skips quietly, so the tool can
sit unconditionally in build scripts.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:      # Python < 3.11
    import tomli as tomllib

KIND_LABEL = {
    "direct": "direct classical theorem",
    "encoding": "classical theorem with encoding choices",
    "composite": "composite interface",
}


def load(census_path: Path, annot_path: Path) -> tuple[dict, dict]:
    census = {k: v for k, v in json.loads(census_path.read_text()).items()
              if v.get("status") == "axiom"}
    annot = {k: v for k, v in json.loads(annot_path.read_text()).items()
             if not k.startswith("_")}
    return census, annot


def validate(census: dict, annot: dict) -> list[str]:
    errors = []
    annot_decls = {v["decl"] for v in annot.values()}
    census_decls = set(census)
    for d in sorted(annot_decls - census_decls):
        errors.append(f"trust-annotations row for {d} has no live census axiom")
    for d in sorted(census_decls - annot_decls):
        errors.append(f"census axiom {d} has no trust-annotations row")
    return errors


def render(census: dict, annot: dict, project: str) -> str:
    """The generated dl: one entry per interface, in census (B-id) order."""
    def sort_key(bid: str):
        m = re.match(r"B(\d+)([a-z]?)", bid)
        return (int(m.group(1)), m.group(2))

    out = ["<dl width=\"narrow\">"]
    for bid in sorted(annot, key=sort_key):
        row = annot[bid]
        decl = row["decl"]
        short = decl.split(".")[-1]
        anchors = census[decl].get("paper_tags", [])
        used = ", ".join(f'<xref ref="{a}"/>' for a in anchors) or "(none)"
        out.append(f"""  <li>
    <title>{bid} ({KIND_LABEL[row['kind']]})</title>
    <p>
      {row['statement']}
      <em>Lean name:</em> <lean project="{project}" ref="{decl}">{short}</lean>.
      <em>Source:</em> {row['source']}.
      <em>Encoding:</em> {row['encoding']}
      <em>Used at:</em> {used}.
    </p>
  </li>""")
    out.append("</dl>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".", type=Path,
                    help="instance root (contains paper.toml)")
    ap.add_argument("--check", action="store_true",
                    help="verify only; exit 1 on census/annotation mismatch or a stale block")
    args = ap.parse_args()

    root = args.root.resolve()
    with open(root / "paper.toml", "rb") as fh:
        config = tomllib.load(fh)
    cfg = config.get("trust_table")
    if not cfg:
        print("gen-trust-table: no [trust_table] section; skipping")
        return 0
    target = root / cfg["target"]

    census, annot = load(root / cfg["census"], root / cfg["annotations"])
    errors = validate(census, annot)
    for e in errors:
        print(f"gen-trust-table ERROR: {e}", file=sys.stderr)
    if errors:
        return 1

    block = render(census, annot, cfg["project"])
    text = target.read_text()
    pat = re.compile(r"(<!-- trust-table:begin[^>]*-->\n).*?(\n<!-- trust-table:end -->)",
                     re.DOTALL)
    if not pat.search(text):
        print(f"gen-trust-table ERROR: no trust-table markers in {target}", file=sys.stderr)
        return 1
    new = pat.sub(lambda m: m.group(1) + block + m.group(2), text)
    if new != text:
        if args.check:
            print(f"gen-trust-table DRIFT: {target.relative_to(root)} is stale "
                  f"(run ingest/trust_table.py)", file=sys.stderr)
            return 1
        target.write_text(new)
        print(f"gen-trust-table: refreshed {target.relative_to(root)}")
    else:
        print("gen-trust-table: table current")
    return 0


if __name__ == "__main__":
    sys.exit(main())

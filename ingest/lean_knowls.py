#!/usr/bin/env python3
"""Build-time registry of doc-gen4 declaration entries for inline knowls.

For every declaration the paper badges (crosswalk/lean-decl-map.json),
extract its rendered entry (signature + docstring) from the assembled
doc-gen4 subset and emit a JS registry; the paper UI opens these inline,
knowl-style, instead of navigating away. Relative links inside an entry are
rewritten to work from the paper's location (../lean/<project>/...).

Run after build-leandocs.sh; writes output/web/lean-knowls.js.
"""
from __future__ import annotations

import argparse
import json
import posixpath
from pathlib import Path

from lxml import html as lh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", type=Path, nargs="?", default=Path.cwd())
    ap.add_argument("--docs", default="output/leandocs/gq2-claude",
                    help="assembled doc-gen4 subset (relative to instance)")
    ap.add_argument("--web-prefix", default="../lean/gq2-claude/",
                    help="URL of the docs subset relative to the paper page")
    ap.add_argument("--declmap", default="crosswalk/lean-decl-map.json",
                    help="tag -> decl-links JSON naming the badged decls "
                         "this registry should cover")
    ap.add_argument("--out", default="output/web/lean-knowls.js")
    args = ap.parse_args()
    root = args.instance.resolve()
    docs = root / args.docs

    declmap = json.load(open(root / args.declmap))
    entries = [e for v in declmap.values() for e in v]
    # private decls have no doc-gen4 page by design; the paper renders their
    # badges unlinked (tex2ptx @nodocs), so they are not "missing" here
    private = {e["decl"] for e in entries if e.get("private")}
    wanted = {e["decl"] for e in entries} - private

    reg: dict[str, dict] = {}
    for page in sorted(docs.rglob("*.html")):
        rel = page.relative_to(docs).as_posix()
        if rel.startswith(("find/", "declarations/")):
            continue
        try:
            tree = lh.parse(str(page)).getroot()
        except Exception:
            continue
        hits = [d for d in tree.xpath('//div[@class="decl"]')
                if d.get("id") in wanted]
        if not hits:
            continue
        base = posixpath.dirname(rel)
        for d in hits:
            for a in d.iter("a"):
                href = a.get("href") or ""
                if href.startswith(("http", "#", args.web_prefix)):
                    continue
                a.set("href", args.web_prefix +
                      posixpath.normpath(posixpath.join(base, href)))
            name = d.get("id")
            inner = "".join(
                lh.tostring(c, encoding="unicode") for c in d)
            reg[name] = {
                "html": inner,
                "href": f"{args.web_prefix}{rel}#{name}",
            }

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.PAPERFORGE_LEAN_KNOWLS = "
                   + json.dumps(reg, ensure_ascii=False) + ";\n")
    missing = sorted(wanted - set(reg))
    print(f"lean-knowls: {len(reg)}/{len(wanted)} declarations "
          f"({out.stat().st_size // 1024}K) -> {out}")
    if private:
        print(f"  {len(private)} private decl(s) badge unlinked:",
              ", ".join(sorted(private)))
    if missing:
        print("  missing:", ", ".join(missing[:6]),
              "…" if len(missing) > 6 else "")


if __name__ == "__main__":
    main()

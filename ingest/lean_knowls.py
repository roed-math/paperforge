#!/usr/bin/env python3
"""Build-time registry of doc-gen4 declaration entries for inline knowls.

For every declaration the paper badges (crosswalk/lean-decl-map.json),
extract its rendered entry (signature + docstring) from the assembled
doc-gen4 subset and emit a JS registry; the paper UI opens these inline,
knowl-style, instead of navigating away. Relative links inside an entry are
rewritten to work from the paper's location (../lean/<project>/...).

Run after the doc-gen4 subset is assembled; writes the registry named by
--out (the UI bundle picks up web-assets/lean-knowls-<project>.js).

    python3 ingest/lean_knowls.py --project my-lean

--project fills the conventional paths for a formalization badged as
<name>; override any of them explicitly for a non-standard layout.
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
    ap.add_argument("--project", default=None,
                    help="badge project name ([formalizations.<key>].name); "
                         "supplies the defaults for --docs/--web-prefix/--out")
    ap.add_argument("--docs", default=None,
                    help="assembled doc-gen4 subset (relative to instance; "
                         "default output/leandocs/<project>)")
    ap.add_argument("--web-prefix", default=None,
                    help="URL of the docs subset relative to the paper page "
                         "(default ../lean/<project>/)")
    ap.add_argument("--declmap", default="crosswalk/lean-decl-map.json",
                    help="tag -> decl-links JSON naming the badged decls "
                         "this registry should cover")
    ap.add_argument("--out", default=None,
                    help="default web-assets/lean-knowls-<project>.js")
    args = ap.parse_args()
    if not args.project and not (args.docs and args.web_prefix and args.out):
        ap.error("--project is required unless --docs, --web-prefix and "
                 "--out are all given explicitly")
    args.docs = args.docs or f"output/leandocs/{args.project}"
    args.web_prefix = args.web_prefix or f"../lean/{args.project}/"
    args.out = args.out or f"web-assets/lean-knowls-{args.project}.js"
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
    # merge-assign so per-formalization registry files can be concatenated
    # into one bundle (decl names are namespaced per project)
    out.write_text("window.PAPERFORGE_LEAN_KNOWLS = Object.assign("
                   "window.PAPERFORGE_LEAN_KNOWLS || {}, "
                   + json.dumps(reg, ensure_ascii=False) + ");\n")
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

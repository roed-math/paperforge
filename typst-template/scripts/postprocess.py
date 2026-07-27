#!/usr/bin/env python3
"""Finish a Typst HTML export into a servable page.

Typst 0.15 has no way to write into the real ``<head>``: an ``html.elem("head")``
in the source is emitted as an ordinary element at the top of ``<body>``. The
library therefore parks the stylesheet and script tags in a
``<template id="pf-head-assets">`` and this script lifts them where they belong.

It is deliberately a small string transform rather than a parse-and-serialize:
Typst's output is machine-generated and regular, and round-tripping it through
an HTML parser would reflow the MathML for no gain.

Usage:
    postprocess.py OUTPUT.html [--assets DIR] [--title TEXT] [--description TEXT]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

TEMPLATE_RE = re.compile(
    r'\s*<template id="pf-head-assets">(?P<inner>.*?)</template>',
    re.DOTALL,
)


def lift_head_assets(html: str) -> tuple[str, str]:
    """Remove the parked template, returning (html, head_fragment)."""
    match = TEMPLATE_RE.search(html)
    if not match:
        return html, ""
    return html[: match.start()] + html[match.end():], match.group("inner").strip()


def inject_head(html: str, fragment: str) -> str:
    if not fragment:
        return html
    idx = html.find("</head>")
    if idx == -1:
        raise SystemExit("no </head> in the Typst output — cannot inject assets")
    return html[:idx] + fragment + html[idx:]


def add_meta(html: str, description: str | None) -> str:
    """Add a description meta tag.

    Note the title is left alone: Typst writes ``<title>`` from
    ``set document(title: ..)``. If that title contains math, substitute the
    Unicode form in the source — nothing typesets math in a browser tab.
    """
    if not description:
        return html
    tag = f'<meta name="description" content="{escape_attr(description)}">'
    idx = html.find("</head>")
    return html[:idx] + tag + html[idx:] if idx != -1 else html


def escape_attr(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def copy_assets(assets: Path, dest: Path) -> list[str]:
    copied = []
    for item in sorted(assets.iterdir()):
        if item.name.startswith("."):
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
        copied.append(item.name)
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="the file typst wrote")
    parser.add_argument("--assets", type=Path, help="directory of CSS/JS to copy alongside")
    parser.add_argument("--description", help="meta description")
    args = parser.parse_args(argv)

    if not args.html.exists():
        raise SystemExit(f"no such file: {args.html}")

    html = args.html.read_text(encoding="utf-8")
    html, fragment = lift_head_assets(html)
    if not fragment:
        print("note: no pf-head-assets template found (nothing to lift)", file=sys.stderr)
    html = inject_head(html, fragment)
    html = add_meta(html, args.description)
    args.html.write_text(html, encoding="utf-8")

    if args.assets:
        if not args.assets.is_dir():
            raise SystemExit(f"not a directory: {args.assets}")
        copied = copy_assets(args.assets, args.html.parent)
        print(f"assets: {', '.join(copied)}")

    print(f"postprocessed {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

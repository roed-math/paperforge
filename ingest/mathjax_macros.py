#!/usr/bin/env python3
"""Inject the paper's LaTeX macros into MathJax's config (tex.macros).

With lazy typesetting (ui/lazy) the hidden #latex-macros div is never
processed — IntersectionObserver does not fire for display:none elements —
so in-document \\newcommand definitions are never seen and every use renders
as a red 'undefined control sequence'. The fix: parse the docinfo macros
from source/main.ptx and write them into the emitted MathJax startup
module's tex.macros, where they exist before any expression is typeset
(in any order). Idempotent; run after `pretext build web`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def match_brace(s: str, i: int) -> int:
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return j
    raise ValueError(f"unbalanced braces at {i}")


def parse_macros(block: str) -> dict:
    """\\newcommand{\\x}{body} / \\newcommand{\\f}[n]{body} -> tex.macros."""
    out = {}
    i = 0
    while True:
        i = block.find(r"\newcommand", i)
        if i < 0:
            break
        j = block.index("{", i)
        k = match_brace(block, j)
        name = block[j + 1:k].strip().lstrip("\\")
        m = re.match(r"\s*\[(\d+)\]", block[k + 1:])
        nargs, b = (int(m.group(1)), k + 1 + m.end()) if m else (0, k + 1)
        j2 = block.index("{", b)
        k2 = match_brace(block, j2)
        body = block[j2 + 1:k2]
        out[name] = [body, nargs] if nargs else body
        i = k2 + 1
    return out


def inject(target: Path, macros: dict) -> bool:
    text = target.read_text()
    line = '    "macros": ' + json.dumps(macros) + ","
    # replace a previous injection, else insert right after the tex block opens
    cleaned = re.sub(r'\n\s*"macros": \{.*?\},(?=\n)', "", text, count=1)
    new, n = re.subn(r'("tex": \{)', r"\1\n" + line.replace("\\", "\\\\"),
                     cleaned, count=1)
    if not n:
        return False
    target.write_text(new)
    return True


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    src = (root / "source/main.ptx").read_text()
    m = re.search(r"<macros>(.*?)</macros>", src, re.S)
    if not m:
        sys.exit("no <macros> block in source/main.ptx")
    macros = parse_macros(m.group(1))
    done = []
    for rel in ("output/web/_static/pretext/js/mathjax_startup.js",
                "output/web/_static/pretext/js/dist/mathjax_startup.js"):
        t = root / rel
        if t.exists() and inject(t, macros):
            done.append(rel)
    print(f"tex.macros ({len(macros)} macros) -> {len(done)} startup file(s)")
    if not done:
        sys.exit("no startup file patched — did pretext build web run?")


if __name__ == "__main__":
    main()

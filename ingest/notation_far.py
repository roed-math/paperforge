#!/usr/bin/env python3
"""notation_far: mark notation used a "long time" after its definition.

Reader-facing motivation: the HTML notation hovers are deliberately invisible
until hover (no knowl underline inside equations). But a symbol whose
definition is many pages back deserves a visible affordance. This transform
marks exactly those uses, per symbol occurrence — including individual symbols
inside a single displayed equation.

Mechanism: a far use ``\\notn{key}{sym}`` is rewritten to ``\\notnfar{key}{sym}``,
where (see docinfo macros)

    \\notnfar{k}{x} = \\class{ptxfar}{\\class{ptxnotn-k}{x}}

so MathJax stamps the occurrence with BOTH the key class (hover wiring) and
``ptxfar`` (a distinct prefix, deliberately NOT ``ptxnotn-``, so the hover JS
never mistakes it for a key). CSS gives ``.ptxfar`` a default-visible dotted
underline; near uses stay invisible until hover.

Distance = words of prose between the key's defining site and the use, in
reading order across the whole document (source files processed in main.ptx
xi:include order). Threshold: ``[notation] far_words`` in paper.toml
(default 1500 ≈ a few pages).

Derived data policy: far-marks are COMPUTED, never hand-written. The transform
is idempotent (existing ``\\notnfar`` marks are normalized back to ``\\notn``
before recomputation) and should re-run after any edit that moves text; the
LaTeX/print outputs are unaffected (both macros typeset their symbol argument;
``\\class`` is MathJax-only and stripped for print via the macro definition).

Uses *before* the definition are left unmarked — that is an error for the
notation_order validator, not a styling concern.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

NOTN = re.compile(r"\\notn(?:far)?\{([^}]*)\}")
NOTATION_EL = re.compile(r"<notation\b[^>]*\bkey=\"([^\"]*)\"")
DEF_OPEN = re.compile(r"<definition\b")
DEF_CLOSE = re.compile(r"</definition>")
TAG = re.compile(r"<[^>]+>")
WORD = re.compile(r"[A-Za-z]{2,}")
INCLUDE = re.compile(r"<xi:include\s+href=\"\./([^\"]+)\"")


def reading_order_files(source: Path) -> list[Path]:
    main = source / "main.ptx"
    files = [main]
    files += [source / h for h in INCLUDE.findall(main.read_text())]
    return [f for f in files if f.exists()]


def word_count(xml_chunk: str) -> int:
    return len(WORD.findall(TAG.sub(" ", xml_chunk)))


def collect_and_rewrite(files: list[Path], far_words: int, dry: bool):
    """Two passes over the same reading order.

    Pass 1: running word position of every \\notn use and every defining site
    (<notation key> element, or first use inside a <definition> block).
    Pass 2: rewrite each use whose distance from its key's definition exceeds
    the threshold.
    """
    defined_at: dict[str, int] = {}
    uses = []          # (file, match-ordinal-within-file, key, word-pos)
    pos = 0
    for f in files:
        text = f.read_text().replace("\\notnfar{", "\\notn{")  # normalize
        cursor = 0
        depth = 0
        events = sorted(
            [(m.start(), "use", m) for m in NOTN.finditer(text)]
            + [(m.start(), "notation", m) for m in NOTATION_EL.finditer(text)]
            + [(m.start(), "defopen", m) for m in DEF_OPEN.finditer(text)]
            + [(m.start(), "defclose", m) for m in DEF_CLOSE.finditer(text)])
        ordinal = 0
        for start, kind, m in events:
            pos += word_count(text[cursor:start])
            cursor = start
            if kind == "notation":
                defined_at.setdefault(m.group(1), pos)
            elif kind == "defopen":
                depth += 1
            elif kind == "defclose":
                depth = max(0, depth - 1)
            else:
                key = m.group(1)
                if depth > 0:
                    defined_at.setdefault(key, pos)
                uses.append((f, ordinal, key, pos))
                ordinal += 1
        pos += word_count(text[cursor:])

    changed = {}
    for f in {u[0] for u in uses}:
        text = f.read_text().replace("\\notnfar{", "\\notn{")
        matches = list(NOTN.finditer(text))
        far_ordinals = {
            ordinal for (uf, ordinal, key, wpos) in uses
            if uf == f and key in defined_at
            and wpos - defined_at[key] > far_words}
        out, last = [], 0
        for k, m in enumerate(matches):
            out.append(text[last:m.start()])
            frag = text[m.start():m.end()]
            if k in far_ordinals:
                frag = frag.replace("\\notn{", "\\notnfar{", 1)
            out.append(frag)
            last = m.end()
        out.append(text[last:])
        new = "".join(out)
        if new != f.read_text():
            changed[f] = len(far_ordinals)
            if not dry:
                f.write_text(new)
    return defined_at, uses, changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", type=Path, nargs="?", default=Path.cwd())
    ap.add_argument("--far-words", type=int, default=None,
                    help="override [notation] far_words (default 1500)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    far_words = args.far_words
    cfg_file = args.instance / "paper.toml"
    if far_words is None and cfg_file.exists():
        with open(cfg_file, "rb") as fh:
            far_words = tomllib.load(fh).get("notation", {}).get("far_words")
    far_words = far_words if far_words is not None else 1500

    files = reading_order_files(args.instance / "source")
    defined, uses, changed = collect_and_rewrite(files, far_words, args.dry_run)
    far_total = sum(changed.values())
    print(f"{len(uses)} \\notn use(s), {len(defined)} defined key(s), "
          f"threshold {far_words} words")
    for f, nfar in sorted(changed.items()):
        print(f"  {'would mark' if args.dry_run else 'marked'} "
              f"{nfar} far use(s) in {f.name}")
    if not changed:
        print("no far uses (or no \\notn tagging yet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

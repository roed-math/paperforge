"""Fixture tests for notation_order and plagiarism.

Runnable directly (no pytest dependency):  python3 tests/test_content_validators.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge_validators import load_config, notation_order, plagiarism  # noqa: E402

MAIN = """<?xml version="1.0" encoding="utf-8"?>
<pretext>
  <article xml:id="paper">
    <section xml:id="sec-a">
      <title>A</title>
      <p>Early use of Qp: <m>\\notn{Qp}{\\mathbf Q_p}</m>.</p>
      <p>Use of undefined key: <m>\\notn{ghost}{G}</m>.</p>
      <definition xml:id="def-qp">
        <statement><p>The field <m>\\notn{Qp}{\\mathbf Q_p}</m> of p-adic numbers.</p></statement>
      </definition>
      <notation key="zhat"><usage><m>\\notn{zhat}{\\widehat{Z}}</m></usage>
        <description>profinite integers</description></notation>
      <p>Fine use after def: <m>\\notn{Qp}{\\mathbf Q_p}</m> and
         <m>\\notn{zhat}{\\widehat{Z}}</m>.</p>
      <p xml:id="p-copy">the quick brown fox jumps over the lazy dog while
         the band plays on and the crowd goes wild tonight</p>
      <p xml:id="p-quote"><q>verbatim words inside an attributed quotation are
         exempt from the check entirely <xref ref="bib-x"/></q></p>
      <p xml:id="p-math"><m>the quick brown fox jumps over the lazy dog</m></p>
    </section>
  </article>
</pretext>
"""

SOURCE_TXT = """The quick brown fox jumps over the lazy dog while the band
plays on and the crowd goes wild tonight. Verbatim words inside an attributed
quotation are exempt from the check entirely."""


def build_instance(root: Path) -> None:
    (root / "source").mkdir(parents=True)
    (root / "source" / "main.ptx").write_text(MAIN)
    (root / "refs").mkdir()
    (root / "refs" / "book.txt").write_text(SOURCE_TXT)
    (root / "paper.toml").write_text(
        '[inputs]\nai_draft = "draft.tex"\nlean_project = "."\n'
        '[plagiarism]\nngram = 7\nerror_run = 12\nsources = ["refs/"]\n')
    # draft contains ONLY the second half of the copied sentence -> the long
    # overlap is pipeline-added, but a sub-span is inherited
    (root / "draft.tex").write_text(
        "the band plays on and the crowd goes wild tonight")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_instance(root)
        cfg = load_config(root)

        # --- notation_order ---
        nf = notation_order.check(cfg)
        msgs = [f"{f.severity}:{f.message[:40]}" for f in nf]
        assert any("'Qp' used before" in f.message and f.severity == "error"
                   for f in nf), msgs
        assert any("'ghost' used" in f.message and "never defined" in f.message
                   for f in nf), msgs
        assert not any("'zhat'" in f.message for f in nf), msgs  # defined+used: clean

        # --- plagiarism ---
        pf = plagiarism.check(cfg)
        pm = [f"{f.severity}:{f.message[:60]}" for f in pf]
        # the 19-word copied span must be an error, located at p-copy
        assert any(f.severity == "error" and "book.txt" in f.message
                   and f.location == "p-copy" for f in pf), pm
        # quoted text and math content must NOT be flagged
        assert not any(f.location in ("p-quote", "p-math") for f in pf), pm
        report = root / "output" / "plagiarism-report.json"
        assert report.exists()

    print("all content-validator fixture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

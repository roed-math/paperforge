"""Fixture test for ingest/notation_far.py (far-use marking, idempotency).

Runnable directly:  python3 tests/test_notation_far.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "ingest" / "notation_far.py"

FILLER = " ".join(f"filler{i} words padding" for i in range(20))  # 60 words

MAIN = """<?xml version="1.0" encoding="utf-8"?>
<pretext xmlns:xi="http://www.w3.org/2001/XInclude">
  <article xml:id="paper">
    <xi:include href="./sec-a.ptx"/>
    <xi:include href="./sec-b.ptx"/>
  </article>
</pretext>
"""

SEC_A = f"""<?xml version="1.0" encoding="utf-8"?>
<section xml:id="sec-a">
  <title>A</title>
  <notation key="zhat"><usage><m>\\widehat{{Z}}</m></usage>
    <description>profinite integers</description></notation>
  <p>Near use right away: <m>\\notn{{zhat}}{{\\widehat Z}}</m>.</p>
  <p>{FILLER}</p>
</section>
"""

SEC_B = f"""<?xml version="1.0" encoding="utf-8"?>
<section xml:id="sec-b">
  <title>B</title>
  <p>{FILLER}</p>
  <p>Far display, two symbols, only zhat is tracked-far:
    <me>\\notn{{zhat}}{{\\widehat Z}} \\to \\notn{{fresh}}{{F}}</me></p>
  <definition xml:id="def-fresh">
    <statement><p><m>\\notn{{fresh}}{{F}}</m> is defined here.</p></statement>
  </definition>
  <p>Near use of fresh: <m>\\notn{{fresh}}{{F}}</m>.</p>
</section>
"""


def run(instance: Path, *args: str) -> str:
    r = subprocess.run([sys.executable, str(SCRIPT), str(instance), *args],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "source").mkdir()
        (root / "source" / "main.ptx").write_text(MAIN)
        (root / "source" / "sec-a.ptx").write_text(SEC_A)
        (root / "source" / "sec-b.ptx").write_text(SEC_B)

        run(root, "--far-words", "50")
        b = (root / "source" / "sec-b.ptx").read_text()
        a = (root / "source" / "sec-a.ptx").read_text()
        # zhat in sec-b is > 50 words after its <notation> definition -> far;
        # the 'fresh' use in the SAME equation is a pre-definition use -> not far
        assert "\\notnfar{zhat}" in b, b
        assert "\\notnfar{fresh}" not in b, b
        # near uses unmarked
        assert "\\notnfar" not in a, a
        assert b.count("\\notnfar") == 1, b

        # idempotent: second run changes nothing
        before = b
        run(root, "--far-words", "50")
        assert (root / "source" / "sec-b.ptx").read_text() == before

        # raising the threshold removes the mark
        run(root, "--far-words", "100000")
        assert "\\notnfar" not in (root / "source" / "sec-b.ptx").read_text()

    print("notation_far fixture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

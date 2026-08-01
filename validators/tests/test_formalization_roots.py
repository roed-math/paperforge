"""formalization_roots + lean_links across both config generations.

The regression this guards: the validators once read only the deprecated
``[inputs] lean_project`` key, so `paperforge check` crashed with
KeyError('lean_project') on every instance `paperforge init` creates, and
on every paper with no formalization at all.

Runnable directly (no pytest dependency):
    python3 validators/tests/test_formalization_roots.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge_validators import (formalization_roots, lean_links,  # noqa: E402
                                   load_config)

MAIN = """<?xml version="1.0" encoding="utf-8"?>
<pretext><article xml:id="paper"><section xml:id="s">
  <title>S</title>
  <theorem xml:id="thm-a"><lean ref="Prim.good">Prim.good</lean>
    <statement><p>x</p></statement></theorem>
  <theorem xml:id="thm-b"><lean ref="Prim.gone">Prim.gone</lean>
    <statement><p>y</p></statement></theorem>
  <theorem xml:id="thm-c"><lean ref="Second.ok" project="second">Second.ok</lean>
    <statement><p>z</p></statement></theorem>
</section></article></pretext>
"""

NEW_SHAPE = """
[paperforge]
instance_schema = 1
[paper]
title = "T"
[inputs]
ai_draft = "draft.tex"
[formalizations.primary]
name = "prim"
root = "lean/prim"
[formalizations.other]
name = "second"
root = "lean/second"
"""

OLD_SHAPE = """
[paper]
title = "T"
[inputs]
ai_draft = "draft.tex"
lean_project = "lean/prim"
lean_project_name = "prim"
[inputs.formalizations.second]
root = "lean/second"
"""

NO_LEAN = """
[paperforge]
instance_schema = 1
[paper]
title = "T"
[inputs]
ai_draft = "draft.tex"
"""


def build(root: Path, paper_toml: str) -> None:
    (root / "source").mkdir(parents=True)
    (root / "source" / "main.ptx").write_text(MAIN)
    (root / "paper.toml").write_text(paper_toml)
    (root / "lean" / "prim").mkdir(parents=True)
    (root / "lean" / "prim" / "Basic.lean").write_text(
        "namespace Prim\ntheorem good : True := trivial\nend Prim\n")
    (root / "lean" / "second").mkdir(parents=True)
    (root / "lean" / "second" / "Basic.lean").write_text(
        "namespace Second\ntheorem ok : True := trivial\nend Second\n")


def check(paper_toml: str):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build(root, paper_toml)
        cfg = load_config(root)
        return formalization_roots(cfg), lean_links.check(cfg)


def main() -> int:
    for label, toml in (("new", NEW_SHAPE), ("old", OLD_SHAPE)):
        roots, findings = check(toml)
        assert set(roots) == {"", "prim", "second"}, (label, sorted(roots))
        assert roots[""] == roots["prim"], label
        msgs = [str(f) for f in findings]
        # the one dangling badge is an error; the two live ones are silent
        assert len(findings) == 1, (label, msgs)
        assert "Prim.gone" in findings[0].message, (label, msgs)
        assert findings[0].severity == "error", (label, msgs)

    # no formalization at all: no crash, badges reported once as a warning
    roots, findings = check(NO_LEAN)
    assert roots == {}, roots
    assert len(findings) == 1 and findings[0].severity == "warning", findings
    assert "no formalization configured" in findings[0].message, findings

    print("formalization_roots / lean_links config-shape tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

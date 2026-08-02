"""paperforge selftest: prove the install works, before touching a real paper.

Runs the whole documented onboarding sequence against the public fixture
(examples/minimal-paper) in a scratch directory, in a subprocess per step —
exactly what a new user is about to type. Nothing outside the scratch
directory is touched, and the scratch directory is removed unless --keep.

The scratch path contains a space on purpose: quoting bugs are the classic
way a pipeline that "works" on the developer's machine fails on someone
else's.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import tool_root
from ._common import fail


def add_parser(sub) -> None:
    p = sub.add_parser("selftest",
                       help="run the fixture paper end to end (verifies the "
                            "install)")
    p.add_argument("--keep", action="store_true",
                   help="keep the scratch instance and print its path")
    p.add_argument("--no-build", action="store_true",
                   help="stop before `build web` (skips the PreTeXt build)")
    p.set_defaults(func=run)


def _pf(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(tool_root()), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return subprocess.run([sys.executable, "-m", "paperforge", *args],
                          cwd=cwd, capture_output=True, text=True, env=env)


class _Steps:
    def __init__(self):
        self.failed: list[str] = []

    def run(self, label: str, proc: subprocess.CompletedProcess,
            expect: int = 0, contains: str = "") -> bool:
        ok = proc.returncode == expect and contains in (proc.stdout
                                                        + proc.stderr)
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
        if not ok:
            self.failed.append(label)
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
            for line in tail:
                print(f"          {line}")
        return ok


def run(args, extra) -> int:
    fixture = tool_root() / "examples" / "minimal-paper"
    if not fixture.is_dir():
        return fail(f"fixture not found at {fixture} — is this a full "
                    f"paperforge checkout?")

    scratch = Path(tempfile.mkdtemp(prefix="paperforge selftest "))
    inst = scratch / "minimal paper"
    inst.mkdir()
    shutil.copytree(fixture / "lean-src", scratch / "lean src")
    print(f"PaperForge selftest\n\n  scratch: {scratch}\n")

    s = _Steps()
    s.run("init", _pf("init", ".", "--non-interactive",
                      "--title", "A Minimal Fixture Paper", "--slug", "minimal",
                      "--lean-root", "../lean src",
                      "--lean-project-name", "minimal-lean", cwd=inst))
    if s.failed:
        return _finish(s, scratch, args.keep)

    shutil.copyfile(fixture / "draft.tex", inst / "inputs/draft/main.tex")
    shutil.copyfile(fixture / "notation-map.json",
                    inst / "notation/notation-map.json")

    s.run("doctor", _pf("doctor", cwd=inst))
    s.run("ingest --bootstrap", _pf("ingest", "--bootstrap", cwd=inst),
          contains="Bootstrap ingestion completed")
    s.run("build web refuses an unreviewed candidate map",
          _pf("build", "web", cwd=inst), expect=1,
          contains="accept lean-decl-map")
    s.run("accept lean-decl-map", _pf("accept", "lean-decl-map", cwd=inst))
    s.run("status", _pf("status", cwd=inst), contains="buildable")

    if args.no_build:
        print("\n  (skipped: build web, check — --no-build)")
    elif shutil.which("pretext") is None:
        print("\n  SKIP  build web, check — the pretext CLI is not installed")
    else:
        if s.run("build web", _pf("build", "web", cwd=inst)):
            page = inst / "output" / "web" / "paper.html"
            html = page.read_text() if page.is_file() else ""
            for label, ok in [
                    ("built page exists", bool(html)),
                    ("formalization badges resolved", "lean-link" in html),
                    ("UI bundle assembled",
                     (inst / "output/web/detail-ui.js").is_file()),
                    ("fonts stylesheet copied",
                     (inst / "output/web/fonts-cm.css").is_file()),
                    ("build provenance written",
                     (inst / "output/build-provenance.json").is_file())]:
                print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
                if not ok:
                    s.failed.append(label)
        # the fixture has real findings (no section summaries, an early
        # notation use): exit 1 with those named IS the pass condition
        s.run("check reports the fixture's known findings",
              _pf("check", cwd=inst), expect=1, contains="section_summaries")

    return _finish(s, scratch, args.keep)


def _finish(s: _Steps, scratch: Path, keep: bool) -> int:
    if keep:
        print(f"\n  kept: {scratch}")
    else:
        shutil.rmtree(scratch, ignore_errors=True)
    if s.failed:
        print(f"\n{len(s.failed)} step(s) failed: {', '.join(s.failed)}")
        print("Run `paperforge doctor` for the environment, and re-run with "
              "--keep to inspect the scratch instance.")
        return 1
    print("\nAll steps passed — the install is working. "
          "Next: `paperforge init` your own paper (docs/GETTING-STARTED.md).")
    return 0

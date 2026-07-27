"""Requirement (G_Q2 July 2026 review §2.2/§3.2): artifacts that duplicate
each other must not drift. Two generators own such duplications and each has
a --check mode; this validator runs them so ``run_all`` gates on drift:

* ingest/trust_table.py --check — the intro trust-base table vs the live
  axiom census (skips without a [trust_table] section);
* sitegen/gen_status.py --check — status.json + the stamped version footers
  vs the live artifacts (skips without a status.json under [site].dir).

Both tools print their own DRIFT/ERROR diagnostics; this validator surfaces
each stderr line as a finding. The fix is always the same: run the named
generator (build-web.sh / build-site.sh do so) and commit the result.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import Finding, instance_root

_PF = Path(__file__).resolve().parents[2]

_GATES = [
    ("trust_table", _PF / "ingest" / "trust_table.py"),
    ("gen_status", _PF / "sitegen" / "gen_status.py"),
]


def check(config: dict) -> list[Finding]:
    root = instance_root(config)
    findings: list[Finding] = []
    for label, tool in _GATES:
        proc = subprocess.run(
            [sys.executable, str(tool), str(root), "--check"],
            capture_output=True, text=True)
        if proc.returncode == 0:
            continue
        lines = [l for l in proc.stderr.splitlines() if l.strip()]
        for line in lines or [f"{label} --check failed (exit {proc.returncode})"]:
            findings.append(Finding("artifact_drift", "error", line, label))
    return findings

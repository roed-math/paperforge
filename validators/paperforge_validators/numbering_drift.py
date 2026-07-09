"""Requirement 13 (bidirectional reference stability): detect numbering drift.

Regenerates the numbering map from the current draft tex (via the ingest
simulator, run as a subprocess) and diffs it against the committed baseline
(``crosswalk/numbering-current.json``):

  - a tag present in the baseline but absent from the regenerated map is an
    ERROR (a statement/equation the Lean side may cite has disappeared or lost
    its label);
  - a tag whose printed number changed is a WARNING (harmless for tag-based
    links, but the Lean-side ledgers and any prose numbers are now stale —
    re-run lean_ledger.py and refresh the baseline);
  - new tags are reported as info-level warnings so the author notices them.

The tag, not the number, is the identity — this validator exists so that
number drift is *noticed and recorded*, never silent.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import Finding, instance_root


def _ingest_script() -> Path:
    # validators/ and ingest/ are sibling dirs of the paperforge checkout
    return Path(__file__).resolve().parents[2] / "ingest" / "tex2ptx.py"


def check(config: dict) -> list[Finding]:
    root = instance_root(config)
    baseline_path = root / config.get("crosswalk", {}).get("dir", "crosswalk") \
        / "numbering-current.json"
    draft = root / config["inputs"]["ai_draft"]
    if not baseline_path.exists():
        return [Finding("numbering_drift", "warning",
                        f"no baseline at {baseline_path}; run tex2ptx --numbering first")]
    if not draft.exists():
        return [Finding("numbering_drift", "error", f"draft not found: {draft}")]

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(_ingest_script()), str(draft),
             "--numbering", str(tmp_path), "--snapshot", "regenerated"],
            capture_output=True, text=True)
        if proc.returncode != 0:
            return [Finding("numbering_drift", "error",
                            f"simulator failed: {proc.stderr.strip()[-300:]}")]
        new = json.load(open(tmp_path))["items"]
    finally:
        tmp_path.unlink(missing_ok=True)
    base = json.load(open(baseline_path))["items"]

    findings: list[Finding] = []
    for tag, rec in base.items():
        if tag not in new:
            findings.append(Finding(
                "numbering_drift", "error",
                f"tag '{tag}' ({rec['kind']} {rec['number']}) vanished from the draft "
                f"— Lean-side citations may dangle", tag))
        elif new[tag]["number"] != rec["number"]:
            findings.append(Finding(
                "numbering_drift", "warning",
                f"'{tag}' renumbered {rec['number']} -> {new[tag]['number']} "
                f"(refresh baseline + regenerate lean ledgers)", tag))
    for tag in new:
        if tag not in base:
            findings.append(Finding(
                "numbering_drift", "warning",
                f"new tag '{tag}' ({new[tag]['kind']} {new[tag]['number']}) not in baseline",
                tag))
    return findings

"""Requirement 11 (drift half): a sidecar directive whose ``target`` xml:id no
longer exists in the source is stale and must fail, so queued feedback cannot be
silently misplaced after a refactor. See ../../docs/DIRECTIVES.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from . import Finding, ptx_files, instance_root

_ID = re.compile(r"xml:id=\"([^\"]+)\"")
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def _all_ids(config: dict) -> set[str]:
    ids: set[str] = set()
    for f in ptx_files(config):
        ids.update(_ID.findall(f.read_text(errors="ignore")))
    return ids


def check(config: dict) -> list[Finding]:
    root = instance_root(config)
    ddir = root / "directives"
    if not ddir.exists():
        return []
    ids = _all_ids(config)
    findings: list[Finding] = []
    for d in sorted(ddir.glob("*.md")):  # directives/applied/ is skipped (not glob-recursive)
        m = _FRONTMATTER.match(d.read_text(errors="ignore"))
        if not m:
            findings.append(Finding("directives", "warning",
                                    "directive has no front matter", d.name))
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        target = meta.get("target")
        if target and target not in ids:
            findings.append(Finding(
                "directives", "error",
                f"directive targets xml:id '{target}', which no longer exists",
                d.name))
    return findings

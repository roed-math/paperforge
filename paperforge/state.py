"""Derived instance state (review §10): computed from artifacts on disk,
never stored as a flag that can drift.

States, in order:
    uninitialized          no valid paper.toml
    scaffolded             config exists; the draft does not
    ready-to-bootstrap     draft exists; no current numbering yet
    bootstrapped-unreviewed candidate decl map(s) awaiting acceptance
    buildable              accepted artifacts present; no web build yet
    built-web              output/web carries a built paper

Each state pairs with the one command that moves it forward.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import InstanceConfig


@dataclass(frozen=True)
class InstanceState:
    name: str
    detail: str
    next_command: str


def candidate_declmap(fm_declmap: Path) -> Path:
    return fm_declmap.with_name(
        fm_declmap.name.replace(".json", ".candidate.json"))


def derive_state(cfg: InstanceConfig) -> InstanceState:
    if not cfg.draft.is_file():
        return InstanceState(
            "scaffolded",
            f"draft not found at {cfg.draft}",
            "put the LaTeX draft in place, then: paperforge doctor")
    numbering = cfg.root / "crosswalk" / "numbering-current.json"
    if not numbering.is_file():
        return InstanceState(
            "ready-to-bootstrap",
            "no current numbering yet",
            "paperforge ingest --bootstrap")
    pending = [fm for fm in cfg.formalizations
               if not fm.declmap.is_file()
               and candidate_declmap(fm.declmap).is_file()]
    if pending:
        names = ", ".join(fm.name for fm in pending)
        return InstanceState(
            "bootstrapped-unreviewed",
            f"candidate declaration map(s) awaiting review: {names}",
            f"review {candidate_declmap(pending[0].declmap).relative_to(cfg.root)}, "
            f"then: paperforge accept lean-decl-map")
    web = cfg.web_output
    if not ((web / "paper.html").is_file() or (web / "index.html").is_file()):
        return InstanceState(
            "buildable",
            "no web build yet",
            "paperforge build web")
    return InstanceState(
        "built-web",
        f"web build present at {web}",
        "paperforge check")

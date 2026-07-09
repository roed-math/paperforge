"""paperforge validators: deterministic, CI-gating checks.

Every check is a callable ``check(config: dict) -> list[Finding]``. Checks never
mutate the source; they only report. ``run_all`` aggregates them and sets the exit
code. See ../../docs/ARCHITECTURE.md for the validator-vs-skill split.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    validator: str
    severity: str  # "error" | "warning"
    message: str
    location: str = ""  # xml:id, file path, or "file:line" when known

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.severity.upper()} ({self.validator}){loc}: {self.message}"


def load_config(root: Path | None = None) -> dict:
    """Load ``paper.toml`` from the instance root (defaults to cwd)."""
    root = Path(root or Path.cwd())
    with open(root / "paper.toml", "rb") as fh:
        data = tomllib.load(fh)
    data["_root"] = str(root)
    return data


def instance_root(config: dict) -> Path:
    return Path(config["_root"])


def ptx_files(config: dict) -> list[Path]:
    """All PreTeXt source files of the instance."""
    src = instance_root(config) / "source"
    return sorted(src.rglob("*.ptx")) if src.exists() else []

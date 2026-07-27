"""Shared helpers for the sitegen tools.

Every tool takes the instance root as an optional positional argument
(default: the current directory) and reads its knobs from paper.toml's
[site] tables — see templates/paper.toml for the annotated shapes.
"""
from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:      # Python < 3.11
    import tomli as tomllib


def load_config(root: Path) -> dict:
    with open(root / "paper.toml", "rb") as fh:
        return tomllib.load(fh)


def site_dir(root: Path, config: dict) -> Path:
    return root / config.get("site", {}).get("dir", "web-assets/site")


def formalization_root(root: Path, config: dict, name: str) -> Path:
    """Resolve a formalization's checkout from its badge-project name:
    [inputs.formalizations.<name>].root, the primary [inputs].lean_project
    when the name matches its basename, else formalizations/<name>."""
    inputs = config.get("inputs", {})
    rec = inputs.get("formalizations", {}).get(name)
    if rec and "root" in rec:
        return root / rec["root"]
    primary = inputs.get("lean_project")
    if primary and Path(primary).name == name:
        p = Path(primary)
        return p if p.is_absolute() else root / p
    return root / "formalizations" / name

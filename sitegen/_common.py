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
    """Resolve a formalization's checkout from its badge-project name.

    Understands both config generations — ``[formalizations.<key>]`` records
    carrying ``name``/``root`` (what `paperforge init` writes) and the
    deprecated ``[inputs] lean_project`` / ``[inputs.formalizations.<name>]``
    shape — and falls back to ``formalizations/<name>``."""
    def _resolve(value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else root / p

    for key, rec in (config.get("formalizations") or {}).items():
        if not isinstance(rec, dict) or "root" not in rec:
            continue
        if rec.get("name", key) == name:
            return _resolve(rec["root"])

    inputs = config.get("inputs", {})
    rec = inputs.get("formalizations", {}).get(name)
    if rec and "root" in rec:
        return _resolve(rec["root"])
    primary = inputs.get("lean_project")
    if primary and Path(primary).name == name:
        return _resolve(primary)
    return root / "formalizations" / name

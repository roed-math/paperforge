"""One authoritative interpretation of instance paths.

Rules (docs/CONFIGURATION.md):
- relative paths in committed or machine-local config are relative to the
  instance root;
- ``~`` is expanded;
- absolute paths pass through;
- URLs never go through filesystem resolution (callers keep URL-like
  values, e.g. ``docs_root``, out of this helper).
"""
from __future__ import annotations

from pathlib import Path


def resolve_instance_path(root: Path, value: str | Path) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (root / p)


def looks_like_url(value: str) -> bool:
    return "://" in value or value.startswith("//")

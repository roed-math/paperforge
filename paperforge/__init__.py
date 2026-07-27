"""paperforge: the deterministic command layer.

The generative work lives in skills/ (agent-executed); the judgment-free
work — scaffolding, environment diagnosis, ingestion orchestration, builds,
validation — lives here, behind the `paperforge` command. See
docs/GETTING-STARTED.md for the user path and docs/ARCHITECTURE.md for the
validator/skill split this package deliberately preserves.
"""
from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

#: Instance schema versions this tool can read (paper.toml [paperforge]
#: instance_schema). Missing means 1 (pre-schema instances).
SUPPORTED_SCHEMAS = {1}


def tool_root() -> Path:
    """The paperforge checkout this package runs from (editable install)."""
    return Path(__file__).resolve().parents[1]

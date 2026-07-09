"""Requirement 8: notation is defined before it is used.

Algorithm (to implement): build the reading order of the assembled document
(`pretext -c assembly` output, so xi:includes and version selection are resolved);
walk it collecting, per notation key, the position of its definition (a
``<notation>`` list entry, or the first ``\\notn{key}{..}`` marked as the defining
use) and every subsequent use; report any use whose position precedes its
definition. Notation keys are the same ``ptxnotn-<key>`` keys the HTML hover uses,
so this check and the hover share one source of truth.

Currently a stub: returns a single warning so `run_all` reports honest status.
"""
from __future__ import annotations

from . import Finding


def check(config: dict) -> list[Finding]:
    return [Finding("notation_order", "warning",
                    "not implemented yet (see module docstring for the algorithm)")]

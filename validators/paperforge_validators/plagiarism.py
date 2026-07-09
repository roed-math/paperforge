"""Requirement 3: flag verbatim overlap between the generated prose and the
sources (AI draft + cited PDFs). See ../../docs/PLAGIARISM.md.

Algorithm (to implement): build an n-gram (default 7-word) shingle index over the
sources in ``plagiarism[sources]``; extract prose text from the assembled PreTeXt
(excluding math, ``verbatim`` directives, and attributed ``<q>``/``<blockquote>``);
report each prose shingle that hits the index, with its xml:id location and the
matched source, ranked by span length. Reports only; never edits.

Currently a stub.
"""
from __future__ import annotations

from . import Finding


def check(config: dict) -> list[Finding]:
    return [Finding("plagiarism", "warning",
                    "not implemented yet (see module docstring for the algorithm)")]

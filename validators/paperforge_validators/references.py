"""Requirement 10 (stage 1): references are specific and correct against the local
PDFs in ``references/``.

Algorithm (to implement): for each citation, resolve its bib entry, locate the
matching PDF in ``references[pdf_dir]``, and check the *specific* claims the text
attaches to the citation — a named theorem/section/page should actually appear in
that PDF. Extract PDF text (pdfminer/pypdf), and for each "[Author, Thm 3.2]"-style
pin, verify the referenced label exists. Report pins that cannot be located.

Stage 2 (a human double-check) is out of scope for the validator by design; this
stage only narrows what the human must read.

Currently a stub.
"""
from __future__ import annotations

from . import Finding


def check(config: dict) -> list[Finding]:
    return [Finding("references", "warning",
                    "not implemented yet (see module docstring for the algorithm)")]

"""Requirement 6: every section carries a summary. In PreTeXt this is an
``<introduction>`` child of the division. The *quality/difficulty-grading* of the
summary is a skill (skills/section-summaries); this validator only enforces
*presence*, which is the objective part.
"""
from __future__ import annotations

from lxml import etree

from . import Finding, ptx_files

# Divisions we require a summary for (requirement 6 targets sections; finer
# divisions are the section-summaries skill's judgment call, not a gate).
_DIVISIONS = {"chapter", "section", "appendix"}


def check(config: dict) -> list[Finding]:
    findings: list[Finding] = []
    parser = etree.XMLParser(recover=True, resolve_entities=False)
    for f in ptx_files(config):
        try:
            tree = etree.fromstring(f.read_text(errors="ignore").encode(), parser)
        except etree.XMLSyntaxError as e:
            findings.append(Finding("section_summaries", "warning",
                                    f"could not parse: {e}", f.name))
            continue
        if tree is None:
            continue
        for div in tree.iter():
            if div.tag not in _DIVISIONS:
                continue
            has_intro = any(child.tag == "introduction" for child in div)
            if not has_intro:
                xid = div.get("{http://www.w3.org/XML/1998/namespace}id") or "?"
                findings.append(Finding(
                    "section_summaries", "error",
                    f"<{div.tag}> has no <introduction> summary", f"{f.name}#{xid}"))
    return findings

"""Shared access to the assembled PreTeXt document (xi:includes resolved).

Both content validators (notation_order, plagiarism) need the document in
reading order with location tracking; this module owns that logic so they can
never disagree about what "the document" is.
"""
from __future__ import annotations

from lxml import etree

from . import instance_root

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# Content that is not prose: math, code, formalization badges, raw biblio
# entries (citations of a work legitimately echo that work's own words).
MATH_TAGS = {"m", "me", "men", "md", "mdn", "mrow"}
NON_PROSE_TAGS = MATH_TAGS | {"c", "pre", "cline", "lean", "macros",
                              "latex-image-preamble", "biblio", "usage",
                              "cd", "code", "input", "output", "idx"}


def load_assembled(config) -> etree._Element:
    """Parse source/main.ptx and resolve xi:includes; returns the root."""
    main = instance_root(config) / "source" / "main.ptx"
    tree = etree.parse(str(main))
    tree.xinclude()
    return tree.getroot()


def _localname(el) -> str | None:
    return etree.QName(el).localname if isinstance(el.tag, str) else None


def _is_attributed_quote(el) -> bool:
    return (_localname(el) in ("q", "blockquote")
            and el.find(".//xref") is not None)


def iter_prose(root) -> list[tuple[str, str]]:
    """Reading-order (text, nearest-xml:id) pairs of PROSE only.

    Skips math/code/badges/bibliography and attributed quotes (a <q> or
    <blockquote> containing an <xref> is scholarly citation, not plagiarism).
    docinfo (macros etc.) is skipped entirely.
    """
    out: list[tuple[str, str]] = []

    def walk(el, ctx_id: str) -> None:
        tag = _localname(el)
        if tag is None:                      # comment / processing instruction
            if el.tail and el.tail.strip():
                out.append((el.tail, ctx_id))
            return
        own_id = el.get(XML_ID) or ctx_id
        skip = (tag in NON_PROSE_TAGS or tag == "docinfo"
                or _is_attributed_quote(el))
        if not skip:
            if el.text and el.text.strip():
                out.append((el.text, own_id))
            for child in el:
                walk(child, own_id)
        if el.tail and el.tail.strip():      # tail belongs to the parent flow
            out.append((el.tail, ctx_id))

    walk(root, "document")
    return out


def nearest_id(el) -> str:
    for anc in [el] + list(el.iterancestors()):
        if isinstance(anc.tag, str) and anc.get(XML_ID):
            return anc.get(XML_ID)
    return "document"

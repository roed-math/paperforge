#!/usr/bin/env python3
"""Build-time registry of division summaries for section-xref popups.

For every division in the built single-page HTML (section / appendix /
subsection / subsubsection) that opens with prose — an <introduction>
block (validated by the section_summaries gate for top-level divisions)
or leading paragraphs — extract a short rendered summary and emit a JS
registry. The paper UI intercepts clicks on division cross-references
and shows the summary in place, knowl-style, with a "view in context"
link, instead of jumping away. Divisions with no leading prose (e.g. a
subsection that opens directly with a lemma) stay plain links.

Same single-page assumption as the notation registry: hrefs are
'#<tag>' within paper.html. Run after `pretext build web`; writes
web-assets/section-summaries.js (concatenated into the UI bundle by
build-web.sh, registries before wiring).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lxml import html as lh

DIVISION_CLASSES = {"section", "appendix", "subsection", "subsubsection"}
MAX_PARAS = 2
MAX_CHARS = 900


def clean(el):
    """Strip attributes that would misbehave on a copy inside a popup:
    duplicate ids, and knowl affordances whose handlers are not bound on
    dynamically inserted content (their href would still jump)."""
    for node in el.iter():
        for attr in ("id", "data-knowl", "data-reveal-label",
                     "data-close-label"):
            node.attrib.pop(attr, None)
    return el


def summary_paras(div):
    """The division's leading prose: its <introduction> paragraphs when
    present, else the run of div.para children before the first block."""
    intro = div.xpath('./section[@class="introduction"]')
    if intro:
        pool = intro[0].xpath('./div[contains(@class,"para")]')
    else:
        pool = []
        for child in div:
            cls = set((child.get("class") or "").split())
            if child.tag == "div" and "para" in cls:
                pool.append(child)
            elif child.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                continue
            else:
                break  # first non-prose block ends the leading run
    out, total = [], 0
    for p in pool[:MAX_PARAS]:
        html = lh.tostring(clean(p), encoding="unicode")
        if out and total + len(html) > MAX_CHARS:
            break
        out.append(html)
        total += len(html)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", type=Path, nargs="?", default=Path.cwd())
    ap.add_argument("--html", default="output/web/paper.html")
    ap.add_argument("--out", default="web-assets/section-summaries.js")
    args = ap.parse_args()
    root = args.instance.resolve()

    tree = lh.parse(str(root / args.html)).getroot()
    reg: dict[str, dict] = {}
    skipped = []
    for div in tree.xpath("//section[@id]"):
        cls = set((div.get("class") or "").split())
        if not cls & DIVISION_CLASSES:
            continue
        heading = div.find("./h1")
        for h in ("h2", "h3", "h4", "h5", "h6"):
            if heading is None:
                heading = div.find("./" + h)
        if heading is None:
            continue
        typ = heading.findtext('.//span[@class="type"]', "").strip()
        num = heading.findtext('.//span[@class="codenumber"]', "").strip()
        title_el = heading.find('.//span[@class="title"]')
        title = (lh.tostring(clean(title_el), encoding="unicode")
                 if title_el is not None else "")
        # inner HTML only: drop the wrapping <span class="title">
        if title.startswith("<span"):
            title = title[title.index(">") + 1:title.rindex("<")]
        paras = summary_paras(div)
        if not paras:
            skipped.append(div.get("id"))
            continue
        reg[div.get("id")] = {
            "label": f"{typ} {num}".strip(),
            "title": title,
            "html": "".join(paras),
        }

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.PAPERFORGE_SECTION_SUMMARIES = "
                   + json.dumps(reg, ensure_ascii=False) + ";\n")
    print(f"section-summaries: {len(reg)} divisions "
          f"({out.stat().st_size // 1024}K) -> {out}")
    if skipped:
        print(f"  {len(skipped)} division(s) open with a block, no popup:",
              ", ".join(skipped[:5]), "…" if len(skipped) > 5 else "")


if __name__ == "__main__":
    main()

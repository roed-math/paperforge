#!/usr/bin/env python3
"""Extract homepage background knowls from the built paper.

For each background cluster the homepage links (paper.toml
[site.bg_knowls].clusters), take the first paragraph of that cluster's
subsection from the built web paper, rewrite its internal links to work
from the site root, and emit <site>/bg-knowls.js:

    window.<PREFIX>_KNOWLS = { "bg-demushkin": {"title": ..., "html": ...,
                               "href": "paper/paper.html#bg-demushkin"}, ... }
    window.<PREFIX>_MACROS = { "\\Zp": "...", ... }

where <PREFIX> is [site.bg_knowls].js_global_prefix and the macros are the
paper's \\newcommand block (for KaTeX rendering inside the knowls).  The
homepage's toggle script opens these inline, knowl-style, with a "view in
context" link into the paper's background appendix.  Run after build-web
(build-site.sh invokes this before assembling the site tree).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from lxml import html as lh

from _common import load_config, site_dir


def fix_links(el) -> None:
    """Rewrite hrefs relative to paper/ so they resolve from the site root."""
    for a in el.iter("a"):
        href = a.get("href") or ""
        if href.startswith("#"):
            a.set("href", "paper/paper.html" + href)
        elif href.startswith("../"):
            a.set("href", href[3:])
        elif href and not href.startswith(("http", "paper/", "mailto:")):
            a.set("href", "paper/" + href)
        # PreTeXt knowl attributes are meaningless outside the paper page.
        for attr in list(a.attrib):
            if attr.startswith("data-"):
                del a.attrib[attr]


def parse_macros(main: Path) -> dict:
    """The paper's \\newcommand block, as a KaTeX macros object."""
    text = main.read_text()
    out = {}
    for m in re.finditer(
            r"\\newcommand\{(\\[A-Za-z]+)\}(\[\d+\])?\{", text):
        name, start = m.group(1), m.end() - 1
        depth, j = 0, start
        while j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            if depth == 0:
                break
            j += 1
        out[name] = text[start + 1:j]
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    config = load_config(root)
    cfg = config.get("site", {}).get("bg_knowls", {})
    clusters = cfg.get("clusters", [])
    if not clusters:
        print("gen-bg-knowls: no [site.bg_knowls].clusters configured; skipping")
        return 0
    prefix = cfg.get("js_global_prefix", "PF_BG")
    web_output = config.get("build", {}).get("web_output", "output/web")
    paper = root / web_output / "paper.html"
    main_ptx = root / "source" / "main.ptx"
    out = site_dir(root, config) / "bg-knowls.js"

    tree = lh.parse(str(paper)).getroot()
    reg = {}
    for slug in clusters:
        sec = tree.get_element_by_id(slug, None)
        if sec is None:
            print(f"gen-bg-knowls ERROR: no section #{slug} in {paper}",
                  file=sys.stderr)
            return 1
        tspan = sec.find(".//span[@class='title']")
        title = tspan.text_content() if tspan is not None else slug
        # First real prose paragraph of the subsection (PreTeXt emits
        # paragraphs as <div class="para">).
        para = None
        for p in sec.iter("div"):
            if "para" in (p.get("class") or "").split() and \
                    (p.text_content() or "").strip():
                para = p
                break
        if para is None:
            print(f"gen-bg-knowls ERROR: no paragraph under #{slug}",
                  file=sys.stderr)
            return 1
        fix_links(para)
        reg[slug] = {
            "title": title.strip(),
            "html": lh.tostring(para, encoding="unicode"),
            "href": f"paper/paper.html#{slug}",
        }
    out.write_text(f"window.{prefix}_KNOWLS = "
                   + json.dumps(reg, ensure_ascii=False, sort_keys=True)
                   + f";\nwindow.{prefix}_MACROS = "
                   + json.dumps(parse_macros(main_ptx), ensure_ascii=False,
                                sort_keys=True)
                   + ";\n")
    print(f"gen-bg-knowls: {len(reg)} clusters -> {out.relative_to(root)} "
          f"({out.stat().st_size // 1024}K)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Extract homepage knowls from the built paper.

Two kinds of entries, both configured under paper.toml [site.bg_knowls] and
emitted together into <site>/bg-knowls.js:

* clusters: for each background cluster the homepage links, take the first
  paragraph of that cluster's subsection from the built web paper.

* statements: whole elements (theorem articles, notation paragraphs) stitched
  together in order, so the homepage can show e.g. a main theorem inline,
  complete with the paragraphs that define its notation:

      [[site.bg_knowls.statements]]
      key = "thm-main"
      title = "Theorem 1.2 (Presentation theorem)"
      href = "paper/paper.html#thm-main"
      ids = ["sec-intro-2-2", "sec-intro-2-3", "thm-main"]
      expect = ["odd prime", "conventions", "Presentation theorem"]

  `expect` is a parallel list of substrings that must appear in each
  element's text.  PreTeXt auto-numbers positional ids (sec-*-2-3), so after
  a renumber an id can silently point at a different paragraph; the guard
  turns that drift into a build failure.

Internal links are rewritten to work from the site root, and the output is

    window.<PREFIX>_KNOWLS = { "bg-demushkin": {"title": ..., "html": ...,
                               "href": "paper/paper.html#bg-demushkin"}, ... }
    window.<PREFIX>_MACROS = { "\\Zp": "...", ... }

where <PREFIX> is [site.bg_knowls].js_global_prefix and the macros are the
paper's \\newcommand block (for KaTeX rendering inside the knowls).  The
homepage's toggle script opens these inline, knowl-style, with a "view in
context" link into the paper.  Run after build-web (build-site.sh invokes
this before assembling the site tree).
"""
from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
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


def strip_chrome(el, heading: bool = False) -> None:
    """Drop paper-page chrome that has no behavior on the homepage: the
    hover permalinks, and (for statements) the article heading, which would
    duplicate the panel's own title line."""
    for d in list(el.iter("div")):
        if "autopermalink" in (d.get("class") or "").split():
            d.getparent().remove(d)
    if heading:
        for h in list(el.iter("h1", "h2", "h3", "h4", "h5", "h6")):
            if "heading" in (h.get("class") or "").split():
                h.getparent().remove(h)


def _match_brace(text: str, i: int) -> int:
    """Index of the '}' closing the '{' at position i."""
    depth = 0
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            return j
    raise ValueError(f"unbalanced braces at {i}: {text[i:i + 40]!r}")


def strip_notn(text: str) -> str:
    """Replace \\notn{key}{tex} and \\notnfar{key}{tex} with {tex}.  The
    marked-notation wrappers expand to \\class, which needs the paper page's
    MathJax hover machinery; KaTeX string macros cannot take arguments, so on
    the homepage we render just the notation itself."""
    pat = re.compile(r"\\notn(?:far)?\{")
    while True:
        m = pat.search(text)
        if m is None:
            return text
        i = m.end() - 1                    # '{' opening the key argument
        j = _match_brace(text, i)
        if j + 1 >= len(text) or text[j + 1] != "{":
            raise ValueError(f"\\notn without adjacent second argument: "
                             f"{text[m.start():m.start() + 40]!r}")
        k = _match_brace(text, j + 1)
        text = text[:m.start()] + text[j + 1:k + 1] + text[k + 1:]


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


def extract_cluster(tree, slug: str, paper: Path) -> dict | None:
    sec = tree.get_element_by_id(slug, None)
    if sec is None:
        print(f"gen-bg-knowls ERROR: no section #{slug} in {paper}",
              file=sys.stderr)
        return None
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
        return None
    para = deepcopy(para)
    strip_chrome(para)
    fix_links(para)
    return {
        "title": title.strip(),
        "html": strip_notn(lh.tostring(para, encoding="unicode")),
        "href": f"paper/paper.html#{slug}",
    }


def extract_statement(tree, spec: dict, paper: Path) -> dict | None:
    key = spec.get("key", "?")
    ids = spec.get("ids", [])
    expect = spec.get("expect", [])
    if not (key and spec.get("title") and spec.get("href") and ids):
        print(f"gen-bg-knowls ERROR: statement {key!r} needs key, title, "
              "href, and ids", file=sys.stderr)
        return None
    if expect and len(expect) != len(ids):
        print(f"gen-bg-knowls ERROR: statement {key!r}: expect must "
              "parallel ids", file=sys.stderr)
        return None
    parts = []
    for i, eid in enumerate(ids):
        el = tree.get_element_by_id(eid, None)
        if el is None:
            print(f"gen-bg-knowls ERROR: no element #{eid} in {paper} "
                  f"(statement {key!r})", file=sys.stderr)
            return None
        if expect and expect[i] not in (el.text_content() or ""):
            print(f"gen-bg-knowls ERROR: #{eid} no longer contains "
                  f"{expect[i]!r}; the paper was renumbered under "
                  f"statement {key!r} - update its ids", file=sys.stderr)
            return None
        el = deepcopy(el)
        strip_chrome(el, heading=True)
        fix_links(el)
        parts.append(lh.tostring(el, encoding="unicode"))
    return {
        "title": spec["title"],
        "html": strip_notn("".join(parts)),
        "href": spec["href"],
    }


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    config = load_config(root)
    cfg = config.get("site", {}).get("bg_knowls", {})
    clusters = cfg.get("clusters", [])
    statements = cfg.get("statements", [])
    if not clusters and not statements:
        print("gen-bg-knowls: no [site.bg_knowls] entries configured; "
              "skipping")
        return 0
    prefix = cfg.get("js_global_prefix", "PF_BG")
    web_output = config.get("build", {}).get("web_output", "output/web")
    paper = root / web_output / "paper.html"
    main_ptx = root / "source" / "main.ptx"
    out = site_dir(root, config) / "bg-knowls.js"

    tree = lh.parse(str(paper)).getroot()
    reg = {}
    for slug in clusters:
        entry = extract_cluster(tree, slug, paper)
        if entry is None:
            return 1
        reg[slug] = entry
    for spec in statements:
        key = spec.get("key", "?")
        if key in reg:
            print(f"gen-bg-knowls ERROR: duplicate knowl key {key!r}",
                  file=sys.stderr)
            return 1
        entry = extract_statement(tree, spec, paper)
        if entry is None:
            return 1
        reg[key] = entry

    macros = parse_macros(main_ptx)
    out.write_text(f"window.{prefix}_KNOWLS = "
                   + json.dumps(reg, ensure_ascii=False, sort_keys=True)
                   + f";\nwindow.{prefix}_MACROS = "
                   + json.dumps(macros, ensure_ascii=False, sort_keys=True)
                   + ";\n")
    print(f"gen-bg-knowls: {len(clusters)} clusters + {len(statements)} "
          f"statements -> {out.relative_to(root)} "
          f"({out.stat().st_size // 1024}K)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

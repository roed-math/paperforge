"""Project-site assembly: gather the built trees into output/site/.

    /            hand-authored site pages ([site] dir, copied whole)
    /paper/      the interactive paper (PreTeXt web build)
    /paper.pdf   the arXiv PDF, when built
    /blueprint*/ Verso blueprint(s) of the formalization(s)
    /lean/       doc-gen4 subsets, one per formalization

Portable by construction: no rsync, no perl, no BSD-only flags — the shell
version this replaces needed all three. Assembles whatever has been built
and names what is missing; a site with no PDF is a warning, never a failure.
"""
from __future__ import annotations

import shutil
from pathlib import Path

#: Finder/AppleDouble litter and editor backups never belong on a web server.
_EXCLUDE_NAMES = {".DS_Store"}
_EXCLUDE_PREFIXES = ("._",)
_EXCLUDE_SUFFIXES = ("~",)

#: VersoBlueprint's DOT header hardcodes small edge arrows and the style is
#: not configurable upstream (GraphDotStyle defaults in
#: VersoBlueprint/src/VersoBlueprint/Graph.lean); they are hard to follow on
#: a large graph, so bump them in the copied tree.
_ARROW_TWEAKS = [
    ("arrowhead=vee, arrowsize=0.6, penwidth=1]",
     "arrowhead=vee, arrowsize=1.05, penwidth=1.25]"),
    ("arrowhead=vee, arrowsize=0.5, penwidth=0.9]",
     "arrowhead=vee, arrowsize=0.9, penwidth=1.1]"),
]


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names
            if n in _EXCLUDE_NAMES
            or n.startswith(_EXCLUDE_PREFIXES)
            or n.endswith(_EXCLUDE_SUFFIXES)}


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def _bump_blueprint_arrows(tree: Path) -> int:
    changed = 0
    targets = [p for p in tree.rglob("*.html")]
    targets += [p for p in tree.rglob("blueprint-manifest.json")]
    for f in targets:
        text = f.read_text(encoding="utf-8", errors="surrogateescape")
        new = text
        for old, repl in _ARROW_TWEAKS:
            new = new.replace(old, repl)
        if new != text:
            f.write_text(new, encoding="utf-8", errors="surrogateescape")
            changed += 1
    return changed


def _dir_size(path: Path) -> str:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    for unit in ("B", "K", "M", "G"):
        if total < 1024 or unit == "G":
            return f"{total:.0f}{unit}" if unit == "B" else f"{total:.1f}{unit}"
        total /= 1024
    return f"{total:.1f}G"


def assemble(cfg, warn) -> str:
    """Build output/site/ from whatever has been built. `warn` receives one
    human-readable line per missing piece."""
    root = cfg.root
    raw = cfg.raw
    site_cfg = raw.get("site", {})
    site = root / "output" / "site"
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)

    parts = []
    source_dir = root / site_cfg.get("dir", "web-assets/site")
    if source_dir.is_dir():
        copy_tree(source_dir, site)
        parts.append("pages")
    else:
        warn(f"no hand-authored site tree at {source_dir} "
             f"(paper.toml [site] dir) — the site has no homepage")

    web = cfg.web_output
    if (web / "paper.html").is_file() or (web / "index.html").is_file():
        copy_tree(web, site / "paper")
        parts.append("paper")
    else:
        warn(f"no web build at {web} — run `paperforge build web` "
             f"(the site has no /paper/)")

    pdf = root / site_cfg.get("pdf", "output/arxiv/main.pdf")
    if pdf.is_file():
        shutil.copyfile(pdf, site / "paper.pdf")
        parts.append("pdf")
    else:
        warn(f"no PDF at {pdf} — run `paperforge build arxiv --pdf` "
             f"(the site has no /paper.pdf)")

    # Verso blueprints: blueprint/ for the primary formalization, plus any
    # sibling blueprint-<name>/ trees.
    for bp in sorted(root.glob("blueprint*")):
        if not bp.is_dir():
            continue
        rendered = bp / "_out" / "site" / "html-multi"
        if (rendered / "index.html").is_file():
            copy_tree(rendered, site / bp.name)
            _bump_blueprint_arrows(site / bp.name)
            parts.append(bp.name)
        else:
            warn(f"{bp.name} not rendered — run {bp.name}/scripts/ci-pages.sh "
                 f"(the site has no /{bp.name}/)")

    leandocs = root / "output" / "leandocs"
    subsets = [d for d in sorted(leandocs.glob("*"))
               if (d / "index.html").is_file()] if leandocs.is_dir() else []
    if subsets:
        copy_tree(leandocs, site / "lean")
        parts.append(f"lean docs ({len(subsets)})")
    elif cfg.formalizations:
        warn("no doc-gen4 subsets under output/leandocs/ "
             "(the site has no /lean/)")

    # PreTeXt, Verso and doc-gen know nothing about the site's favicon; the
    # hand-authored pages carry it themselves. Skips without a favicon.svg.
    _stamp_favicon(site)

    return f"{site} [{', '.join(parts) or 'empty'}] ({_dir_size(site)})"


def _stamp_favicon(site: Path) -> None:
    import importlib.util
    import sys

    from .. import tool_root
    script = tool_root() / "sitegen" / "apply_favicon.py"
    if not script.is_file():
        return
    spec = importlib.util.spec_from_file_location("paperforge_apply_favicon",
                                                  script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    argv = sys.argv
    sys.argv = [str(script), str(site)]
    try:
        mod.main()
    finally:
        sys.argv = argv

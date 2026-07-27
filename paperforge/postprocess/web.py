"""Web-build postprocessing: MathJax lazy loading, ToC default-open,
configured HTML substitutions, the UI asset bundle, and asset copies.

Replaces templates/build-web.sh's in-place seds. Each function returns a
short human status string; a RuntimeError means the expected upstream
pattern vanished (a PreTeXt change) and the build must not pretend the
patch was applied.
"""
from __future__ import annotations

import shutil
from pathlib import Path

_LAZY_ANCHOR = '"input/asciimath",'
_LAZY_PATCHED = '"input/asciimath", "ui/lazy",'
_SIDEBAR_CLOSED = 'class="ptx-sidebar hidden"'
_SIDEBAR_OPEN = 'class="ptx-sidebar"'


def patch_mathjax_lazy(web: Path) -> str:
    """Enable ui/lazy in PreTeXt's emitted MathJax startup module(s)."""
    candidates = [web / "_static/pretext/js/mathjax_startup.js",
                  web / "_static/pretext/js/dist/mathjax_startup.js"]
    found = patched = already = 0
    for f in candidates:
        if not f.is_file():
            continue
        found += 1
        text = f.read_text()
        if _LAZY_PATCHED in text:
            already += 1
            continue
        if _LAZY_ANCHOR not in text:
            raise RuntimeError(
                f"MathJax startup module {f} no longer contains the "
                f"{_LAZY_ANCHOR!r} loader list — PreTeXt output changed; "
                f"refusing to ship without lazy typesetting (update "
                f"postprocess/web.py)")
        f.write_text(text.replace(_LAZY_ANCHOR, _LAZY_PATCHED, 1))
        patched += 1
    if not found:
        raise RuntimeError(
            f"no MathJax startup module found under {web}/_static — "
            f"PreTeXt output layout changed")
    return f"{patched} patched, {already} already lazy"


def open_toc_by_default(web: Path) -> str:
    """Strip the baked 'hidden' class so the wide-screen default-open rule
    in paper-style.css applies (the theme's toggle still closes it)."""
    changed = already = 0
    for f in sorted(web.glob("*.html")):
        text = f.read_text()
        if _SIDEBAR_CLOSED in text:
            f.write_text(text.replace(_SIDEBAR_CLOSED, _SIDEBAR_OPEN))
            changed += 1
        elif _SIDEBAR_OPEN in text:
            already += 1
    if not changed and not already:
        return "no sidebar markup found (single-page fragment build?)"
    return f"{changed} page(s) opened, {already} already open"


def apply_substitutions(web: Path, subs: list[dict]) -> str:
    """[[build.web_substitutions]] from/to literal replacements on the
    built pages (e.g. Unicode for raw title math in HTML metadata)."""
    total = 0
    for f in sorted(web.glob("*.html")):
        text = f.read_text()
        new = text
        for s in subs:
            new = new.replace(s["from"], s["to"])
        if new != text:
            f.write_text(new)
            total += 1
    return f"{total} page(s) substituted"


def assemble_bundle(root: Path, web: Path) -> str:
    """Single UI bundle: registries first, wiring last (html.js.extra does
    not split on spaces — everything must be one file)."""
    wa = root / "web-assets"
    parts: list[Path] = [wa / "notation-registry.js"]
    parts += sorted(wa.glob("lean-knowls-*.js"))     # one per formalization
    if (wa / "section-summaries.js").is_file():
        parts.append(wa / "section-summaries.js")
    parts.append(wa / "detail-ui.js")
    out = web / "detail-ui.js"
    with open(out, "w") as fh:
        for p in parts:
            if p.is_file():
                fh.write(p.read_text())
    return f"{sum(1 for p in parts if p.is_file())} part(s) -> detail-ui.js"


def copy_assets(root: Path, web: Path) -> str:
    wa = root / "web-assets"
    n = 0
    for name in ("detail-ui.css", "paper-style.css", "fonts-cm.css"):
        src = wa / name
        if src.is_file():
            shutil.copyfile(src, web / name)
            n += 1
    fonts = wa / "fonts"
    if fonts.is_dir():
        shutil.copytree(fonts, web / "fonts", dirs_exist_ok=True)
        n += 1
    return f"{n} asset path(s) copied"

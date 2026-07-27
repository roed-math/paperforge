"""paperforge doctor: deterministic environment + instance diagnosis.

Grouped, actionable output; exit 0 when nothing blocks, 1 on a blocking
environment/configuration problem, 2 on command misuse. Reports the actual
tool checkout (commit + dirty state) so paired tool/instance development
stays transparent — dirty is reported, never blocked (review §9).
"""
from __future__ import annotations

import importlib
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .. import tool_root
from ..config import (LOCAL_CONFIG_NAME, ConfigError, InstanceConfig,
                      load_instance)
from ..paths import looks_like_url
from ..provenance import describe_repo, pretext_version
from ..state import derive_state
from ._common import add_instance_arg, resolve_instance

#: (module, why, blocking)
_PY_DEPS = [
    ("lxml", "ingest + validators + sitegen", True),
    ("yaml", "validators", True),
    ("fitz", "PDF page count in version footers (optional)", False),
]

#: (binary, why, blocking)
_BINARIES = [
    ("pretext", "the PreTeXt builds", True),
    ("latexmk", "the arXiv/print PDFs", False),
    ("pdftotext", "plagiarism + reference pin checks", False),
    ("xsltproc", "author-metadata step", False),
    ("xmllint", "author-metadata step", False),
    ("npm", "vendored MathJax + favicon fonts (optional)", False),
    ("rsvg-convert", "favicon rasters (optional)", False),
]

#: PreTeXt versions the XSL overrides are exercised against.
_PRETEXT_EXERCISED = re.compile(r"^2\.4[3-9]\b")


class Report:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def ok(self, msg: str) -> None:
        print(f"OK      {msg}")

    def info(self, msg: str) -> None:
        print(f"INFO    {msg}")

    def warn(self, msg: str) -> None:
        self.warnings += 1
        print(f"WARN    {msg}")

    def error(self, msg: str) -> None:
        self.errors += 1
        print(f"ERROR   {msg}")


def add_parser(sub) -> None:
    p = sub.add_parser("doctor", help="diagnose environment + instance")
    add_instance_arg(p)
    p.set_defaults(func=run)


def _check_environment(rep: Report) -> None:
    v = sys.version_info
    if v >= (3, 11):
        rep.ok(f"Python {platform.python_version()} ({sys.executable})")
    else:
        rep.error(f"Python {platform.python_version()} — 3.11+ required "
                  f"(tomllib); this is {sys.executable}")
    for mod, why, blocking in _PY_DEPS:
        try:
            importlib.import_module(mod)
            rep.ok(f"python package {mod}")
        except ImportError:
            (rep.error if blocking else rep.warn)(
                f"python package {mod} missing — needed for {why}"
                + ("" if blocking else "; that step will be skipped/degraded"))

    d = describe_repo(tool_root())
    rep.ok(f"paperforge checkout: {tool_root()}")
    if d["commit"]:
        rep.info(f"checkout commit: {d['commit'][:7]}"
                 + (" (dirty)" if d["dirty"] else ""))

    for binary, why, blocking in _BINARIES:
        path = shutil.which(binary)
        if path:
            rep.ok(f"{binary} ({path})")
        else:
            (rep.error if blocking else rep.warn)(
                f"{binary} not found — needed for {why}")
    pv = pretext_version()
    if pv:
        if _PRETEXT_EXERCISED.match(pv):
            rep.ok(f"PreTeXt {pv}")
        else:
            rep.warn(f"PreTeXt {pv} — the XSL overrides are exercised against "
                     f"2.43.x; expect drift on other versions")


def _check_instance(rep: Report, cfg: InstanceConfig) -> None:
    rep.ok(f"instance: {cfg.root}")
    rep.ok(f"instance schema: {cfg.schema} (supported)")
    for dep in cfg.deprecations:
        rep.info(f"deprecated config: {dep} (see `paperforge migrate config`)")
    if cfg.local:
        rep.ok(f"machine-local config: {LOCAL_CONFIG_NAME}")

    if cfg.draft.is_file():
        rep.ok(f"draft: {cfg.draft}")
    else:
        rep.error(f"draft not found: {cfg.draft} "
                  f"(paper.toml [inputs] ai_draft)")

    for fm in cfg.formalizations:
        tag = "primary" if fm.primary else fm.name
        if fm.root.is_dir():
            rep.ok(f"formalization {tag}: {fm.root}")
        else:
            rep.error(f"formalization {tag} root not found: {fm.root}")
        if fm.docs_root and not looks_like_url(fm.docs_root) \
                and fm.docs_root.startswith("/"):
            rep.warn(f"formalization {tag} docs_root looks like a local "
                     f"absolute path: {fm.docs_root} — it should be a URL "
                     f"or a deployed URL prefix")

    core = cfg.pretext_core_xsl
    if core is not None:
        if core.is_file():
            rep.ok(f"PreTeXt core XSL: {core}")
        else:
            rep.error(f"PreTeXt core XSL not found: {core}\n"
                      f"        set [build] pretext_core_xsl in "
                      f"{LOCAL_CONFIG_NAME}")
        for sibling in ("pretext-latex.xsl", "pretext-latex-classic.xsl"):
            if core.parent.joinpath(sibling).is_file():
                rep.ok(f"core sibling {sibling}")
            else:
                rep.warn(f"core sibling missing: {core.parent / sibling} — "
                         f"the LaTeX targets need it")

    # machine-local core shims: regenerate when the instance uses them
    shim_dir = cfg.root / "xsl" / "core-local"
    uses_shims = any("core-local/" in (cfg.root / "xsl" / n).read_text()
                     for n in ("custom-html.xsl",)
                     if (cfg.root / "xsl" / n).is_file())
    if uses_shims:
        from .initcmd import discover_core_xsl, write_core_shims
        core_html = core if (core and core.is_file()) else discover_core_xsl()
        if core_html is None:
            rep.error("xsl/core-local shims needed but no PreTeXt core "
                      "found — install pretext, then rerun doctor")
        else:
            stale = not (shim_dir / "html.xsl").is_file() or \
                str(core_html) not in (shim_dir / "html.xsl").read_text()
            if stale:
                for w in write_core_shims(cfg.root, core_html):
                    rep.warn(w)
                rep.ok(f"regenerated xsl/core-local shims -> {core_html.parent}")
            else:
                rep.ok("xsl/core-local shims current")

    # unresolved scaffold placeholders (committed files only, cheap scan)
    hits = []
    for pattern in ("xsl/*.xsl", "scripts/*.sh", "project.ptx"):
        for f in cfg.root.glob(pattern):
            try:
                if "@@" in f.read_text(errors="ignore"):
                    hits.append(f.relative_to(cfg.root))
            except OSError:
                pass
    if hits:
        rep.error("unresolved @@PLACEHOLDER@@ markers in: "
                  + ", ".join(str(h) for h in hits))
    else:
        rep.ok("no unresolved scaffold placeholders")

    for rel in ("source", "content/insertions", "crosswalk", "references"):
        if (cfg.root / rel).is_dir():
            rep.ok(f"dir {rel}/")
        else:
            rep.warn(f"dir {rel}/ missing (created on demand by "
                     f"init/ingest)")


def run(args, extra) -> int:
    rep = Report()
    print("PaperForge doctor\n")
    _check_environment(rep)
    print()
    cfg = None
    try:
        root = resolve_instance(args)
        cfg = load_instance(root)
    except ConfigError as e:
        if args.instance:
            rep.error(str(e))
        else:
            rep.info(f"not inside an instance ({e})")
    if cfg is not None:
        _check_instance(rep, cfg)
        st = derive_state(cfg)
        print(f"\nState: {st.name} — {st.detail}")
        print(f"Next: {st.next_command}")
    print(f"\n{rep.errors} error(s), {rep.warnings} warning(s)")
    return 1 if rep.errors else 0

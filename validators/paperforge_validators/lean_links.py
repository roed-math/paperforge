"""Requirement 12: every ``<lean ref="...">`` points at a declaration that exists
in the current Lean project. A `checkdecls` analog (cf. leanblueprint) that guards
against formalization drift.

Reference implementation: this is the *pattern* the other validators follow.

Approximation: declaration names are collected by scanning ``*.lean`` source with a
namespace stack, rather than from the compiled environment. That is enough to catch
the common failure (a decl renamed/removed by a refactor) but can miss names
produced by macros/`open`/aliases. A production version should read the compiled
environment or doc-gen4 output. Approximations are reported as warnings, hard
misses as errors.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import Finding, ptx_files, instance_root

_LEAN_REF = re.compile(r"<lean\b[^>]*\bref=\"([^\"]+)\"")


def _load_scanner():
    """Reuse the comment- and section-aware scanner from ingest/lean_declmap.py
    (kept there so the extractor and this validator can never disagree)."""
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "ingest" / "lean_declmap.py"
    spec = importlib.util.spec_from_file_location("paperforge_lean_declmap", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.iter_decls


def _lean_decls(project: Path) -> set[str]:
    iter_decls = _load_scanner()
    return {full for full, _doc, _f, _ln, _private in iter_decls(project)}


def _refs(config: dict) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for f in ptx_files(config):
        for ref in _LEAN_REF.findall(f.read_text(errors="ignore")):
            out.append((ref, f))
    return out


def check(config: dict) -> list[Finding]:
    project = Path(config["inputs"]["lean_project"])
    if not project.exists():
        return [Finding("lean_links", "error",
                        f"lean_project does not exist: {project}")]
    decls = _lean_decls(project)
    basenames = {n.rsplit(".", 1)[-1] for n in decls}

    findings: list[Finding] = []
    for ref, f in _refs(config):
        if ref in decls:
            continue
        loc = f"{f.name}"
        if ref.rsplit(".", 1)[-1] in basenames:
            findings.append(Finding(
                "lean_links", "warning",
                f"<lean ref=\"{ref}\"> not found as a fully-qualified name, but its "
                f"base name exists (namespace/alias mismatch?)", loc))
        else:
            findings.append(Finding(
                "lean_links", "error",
                f"<lean ref=\"{ref}\"> matches no declaration in {project.name}", loc))
    return findings

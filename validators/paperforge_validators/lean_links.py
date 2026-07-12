"""Requirement 12: every ``<lean ref="...">`` points at a declaration that exists
in the Lean project it badges. A `checkdecls` analog (cf. leanblueprint) that
guards against formalization drift.

Reference implementation: this is the *pattern* the other validators follow.

Project-aware: a badge carrying ``project="name"`` is validated against that
project's tree — [inputs.formalizations.<name>] in paper.toml gives the root;
badges without a project (or with an unlisted one) validate against the
primary ``inputs.lean_project``.

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

_LEAN_TAG = re.compile(r"<lean\b[^>]*ref=\"[^\"]+\"[^>]*>")
_REF = re.compile(r"\bref=\"([^\"]+)\"")
_PROJ = re.compile(r"\bproject=\"([^\"]+)\"")


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
    return {full for full, _doc, _f, _ln, _private, _kind in iter_decls(project)}


def _refs(config: dict) -> list[tuple[str, str, Path]]:
    out: list[tuple[str, str, Path]] = []
    for f in ptx_files(config):
        for tag in _LEAN_TAG.findall(f.read_text(errors="ignore")):
            ref = _REF.search(tag)
            proj = _PROJ.search(tag)
            out.append((ref.group(1), proj.group(1) if proj else "", f))
    return out


def check(config: dict) -> list[Finding]:
    primary = Path(config["inputs"]["lean_project"])
    roots: dict[str, Path] = {"": primary}
    for name, rec in config["inputs"].get("formalizations", {}).items():
        roots[name] = Path(rec["root"])

    findings: list[Finding] = []
    decls: dict[str, set[str]] = {}
    basenames: dict[str, set[str]] = {}
    for name, root in roots.items():
        if not root.exists():
            findings.append(Finding(
                "lean_links", "error",
                f"formalization root does not exist: {root}"
                + (f" (project {name})" if name else "")))
            continue
        decls[name] = _lean_decls(root)
        basenames[name] = {n.rsplit(".", 1)[-1] for n in decls[name]}

    for ref, proj, f in _refs(config):
        key = proj if proj in decls else ""
        if key not in decls:
            continue                      # root missing: already reported
        if ref in decls[key]:
            continue
        loc = f"{f.name}"
        where = roots[key].name
        if ref.rsplit(".", 1)[-1] in basenames[key]:
            findings.append(Finding(
                "lean_links", "warning",
                f"<lean ref=\"{ref}\"> not found as a fully-qualified name, but its "
                f"base name exists in {where} (namespace/alias mismatch?)", loc))
        else:
            findings.append(Finding(
                "lean_links", "error",
                f"<lean ref=\"{ref}\"> matches no declaration in {where}", loc))
    return findings

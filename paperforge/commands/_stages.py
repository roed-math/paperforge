"""Shared build/ingest stages (review §12): named, logged, skipped only for
a documented reason — 'not configured' and 'input missing' are different
messages. Each stage function returns a status string; raising StageError
aborts the run with the stage named.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .. import tool_root
from ..config import InstanceConfig
from ..state import candidate_declmap


class StageError(Exception):
    pass


class Runner:
    def __init__(self, plan_only: bool = False):
        self.plan_only = plan_only
        self.n = 0
        self.stages: list[tuple[str, str]] = []

    def run(self, name: str, fn=None, skip: str | None = None) -> None:
        self.n += 1
        if skip is not None:
            print(f"[{self.n:>2}] {name:<26} skipped ({skip})")
            self.stages.append((name, f"skipped: {skip}"))
            return
        if self.plan_only:
            print(f"[{self.n:>2}] {name:<26} would run")
            self.stages.append((name, "planned"))
            return
        try:
            status = fn() or "OK"
        except StageError:
            raise
        except subprocess.CalledProcessError as e:
            raise StageError(f"stage '{name}' failed (exit {e.returncode}): "
                             f"{' '.join(str(a) for a in e.cmd[:4])} ...")
        except RuntimeError as e:
            raise StageError(f"stage '{name}': {e}")
        print(f"[{self.n:>2}] {name:<26} {status}")
        self.stages.append((name, status))


def _tool(*rel: str) -> Path:
    return tool_root().joinpath(*rel)


def sh(cfg: InstanceConfig, *cmd, capture: bool = False) -> str:
    """Run a tool subprocess from the instance root."""
    r = subprocess.run([str(c) for c in cmd], cwd=cfg.root, text=True,
                       capture_output=capture, check=True)
    return (r.stdout or "").strip() if capture else ""


def py(cfg: InstanceConfig, script: Path, *args, capture: bool = False) -> str:
    return sh(cfg, sys.executable, script, *args, capture=capture)


# ---------------------------------------------------------------------------
# stage functions
# ---------------------------------------------------------------------------

def trust_table(cfg: InstanceConfig) -> str:
    py(cfg, _tool("ingest", "trust_table.py"))
    return "OK"


def trust_check(cfg: InstanceConfig) -> str:
    py(cfg, _tool("ingest", "trust_table.py"), "--check")
    return "OK"


def tex2ptx(cfg: InstanceConfig, bootstrap: bool = False) -> str:
    # committed artifacts record this path — keep it machine-independent
    # whenever the draft lives inside the instance
    draft = cfg.draft
    try:
        draft = draft.relative_to(cfg.root)
    except ValueError:
        pass
    args: list = [draft,
                  "--out", "source",
                  "--numbering", "crosswalk/numbering-current.json",
                  "--snapshot", "current",
                  "--document-id", cfg.document_id,
                  "--source-map", "crosswalk/source-map.json",
                  "--numbering-profile", cfg.numbering_profile,
                  "--notation-map", "notation/notation-map.json",
                  "--disambig", "notation/disambiguation.json",
                  "--extra-biblio", "references/extra-biblio.xml",
                  "--insertions", "content/insertions",
                  "--lean-annotations", "crosswalk/lean-annotations.json"]
    labels = cfg.raw.get("references", {}).get("labels")
    if labels:
        args += ["--bib-labels", labels]
    if cfg.mathbb_letters:
        args += ["--mathbb", cfg.mathbb_letters]
    for src, dst in cfg.literal_rewrites:
        args += ["--rewrite", f"{src}={dst}"]
    for spec in cfg.authors:
        args += ["--author", spec]
    if not bootstrap:
        for fm in cfg.formalizations:
            args += ["--lean-map", f"{fm.name}={fm.declmap}"]
            if fm.badge_cap is not None:
                args += ["--lean-badge-cap", f"{fm.name}={fm.badge_cap}"]
    py(cfg, _tool("ingest", "tex2ptx.py"), *args)
    return "OK"


def author_metadata(cfg: InstanceConfig) -> str:
    """Python port of apply-author-metadata.sh: reconcile the generated
    frontmatter with content/authors.xml (skips while it has no records)."""
    import shutil as _shutil
    authors = cfg.root / "content" / "authors.xml"
    xsl = cfg.root / "xsl" / "apply-author-metadata.xsl"
    source = cfg.root / "source" / "main.ptx"
    if not authors.is_file() or not xsl.is_file():
        return "skipped (no sidecar)"
    # count records with lxml (a hard dependency) — the xsltproc/xmllint
    # binaries are only required once records actually exist
    from lxml import etree
    try:
        records = etree.parse(str(authors)).xpath("/author-metadata/record")
    except etree.XMLSyntaxError as e:
        raise RuntimeError(f"content/authors.xml does not parse: {e}")
    if not records:
        return "skipped (no records)"
    for binary in ("xsltproc", "xmllint"):
        if not _shutil.which(binary):
            raise RuntimeError(f"{binary} not installed but content/authors.xml "
                               f"declares author records")
    out = subprocess.run(
        ["xsltproc", "--nonet", str(xsl), str(source)],
        capture_output=True, text=True, check=True).stdout
    src_lines = source.read_text().splitlines(keepends=True)
    out_lines = out.splitlines(keepends=True)
    if not src_lines[0].startswith('<?xml version="1.0" encoding="utf-8"?>'):
        raise RuntimeError("source/main.ptx does not start with the expected "
                           "XML declaration")
    normalized = "".join(src_lines[:2] + out_lines[2:])
    if not normalized.endswith("\n"):
        normalized += "\n"
    subprocess.run(["xmllint", "--noout", "-"], input=normalized,
                   text=True, check=True)
    if normalized != source.read_text():
        source.write_text(normalized)
        return "reconciled"
    return "already reconciled"


def lean_axioms(cfg: InstanceConfig) -> str:
    fm = cfg.formalization()
    scan_root = fm.root / fm.module if fm.module else fm.root
    args: list = [scan_root,
                  "--current", "crosswalk/numbering-current.json",
                  "--out", "crosswalk/axiom-citations.json",
                  "--seed-aliases", "source/main.ptx",
                  "--aliases-out", "references/bib-aliases.json"]
    ing = cfg.raw.get("ingest", {})
    if ing.get("axioms_old_matched"):
        args += ["--old", ing["axioms_old_matched"]]
    if ing.get("axioms_old_numbering"):
        args += ["--old-numbering", ing["axioms_old_numbering"]]
    py(cfg, _tool("ingest", "lean_axioms.py"), *args)
    return "OK"


def notation_far(cfg: InstanceConfig) -> str:
    py(cfg, _tool("ingest", "notation_far.py"), ".")
    return "OK"


def prose_terms(cfg: InstanceConfig) -> str:
    py(cfg, _tool("ingest", "prose_terms.py"), ".",
       "--report", "crosswalk/prose-terms-report.json")
    return "OK"


def pretext_build(cfg: InstanceConfig, target: str) -> str:
    sh(cfg, "pretext", "build", target)
    return "OK"


def mathjax_macros(cfg: InstanceConfig) -> str:
    py(cfg, _tool("ingest", "mathjax_macros.py"), ".")
    return "OK"


def registries(cfg: InstanceConfig) -> str:
    py(cfg, _tool("ingest", "notation_registry.py"), ".")
    py(cfg, _tool("ingest", "section_summaries_registry.py"), ".")
    return "OK"


def gen_status(cfg: InstanceConfig, check: bool = False) -> str:
    """Refresh (or gate) the stamped version blocks in the site source."""
    args = ["--check"] if check else []
    py(cfg, _tool("sitegen", "gen_status.py"), ".", *args)
    return "OK"


def gen_bg_knowls(cfg: InstanceConfig) -> str:
    py(cfg, _tool("sitegen", "gen_bg_knowls.py"), ".")
    return "OK"


def bootstrap_declmaps(cfg: InstanceConfig) -> list[Path]:
    """Generate candidate declaration maps (never silently accepted)."""
    made = []
    for fm in cfg.formalizations:
        cand = candidate_declmap(fm.declmap)
        py(cfg, _tool("ingest", "lean_declmap.py"), fm.root,
           "--current", "crosswalk/numbering-current.json",
           "--out", cand)
        made.append(cand)
    return made

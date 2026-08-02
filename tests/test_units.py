"""Unit tests: config normalization, path resolution, state derivation,
init behavior, converter genericity, postprocess idempotency. No PreTeXt
or TeX needed."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL))

from paperforge.config import ConfigError, load_instance          # noqa: E402
from paperforge.paths import resolve_instance_path                # noqa: E402
from paperforge.postprocess import web as ppweb                   # noqa: E402
from paperforge.state import derive_state                         # noqa: E402


def _pf(*args, cwd=None):
    return subprocess.run([sys.executable, "-m", "paperforge", *args],
                          cwd=cwd, capture_output=True, text=True,
                          env={"PATH": str(Path(sys.executable).parent),
                               "PYTHONPATH": str(TOOL),
                               "HOME": str(Path.home())})


# ---------------------------------------------------------------- config

OLD_SHAPE = """
[paper]
title = "T"
instance_name = "old-slug"
[inputs]
ai_draft = "inputs/draft/main.tex"
lean_project = "formalizations/prim"
lean_docs_base = "https://example.org/docs/"
[inputs.formalizations.second]
root = "formalizations/second"
module = "Second"
declmap = "crosswalk/second-map.json"
"""

NEW_SHAPE = """
[paperforge]
instance_schema = 1
[paper]
title = "T"
slug = "new-slug"
document_id = "new-doc"
[inputs]
ai_draft = "inputs/draft/main.tex"
[formalizations.primary]
name = "prim"
root = "formalizations/prim"
module = "Prim"
declmap = "crosswalk/lean-decl-map.json"
[formalizations.second]
name = "second"
root = "formalizations/second"
declmap = "crosswalk/second-map.json"
badge_cap = 1
"""


def test_old_shape_normalizes(tmp_path):
    (tmp_path / "paper.toml").write_text(OLD_SHAPE)
    cfg = load_instance(tmp_path)
    assert cfg.slug == "old-slug" and cfg.document_id == "old-slug"
    assert [f.name for f in cfg.formalizations] == ["prim", "second"]
    assert cfg.formalizations[0].primary
    assert cfg.formalizations[0].root == tmp_path / "formalizations/prim"
    assert cfg.formalizations[0].docs_root == "https://example.org/docs/"
    assert cfg.deprecations           # old keys reported, not fatal


def test_new_shape_no_deprecations(tmp_path):
    (tmp_path / "paper.toml").write_text(NEW_SHAPE)
    cfg = load_instance(tmp_path)
    assert cfg.document_id == "new-doc"
    assert cfg.formalizations[0].module == "Prim"
    assert cfg.formalizations[1].badge_cap == 1
    assert not cfg.deprecations


def test_unsupported_schema_fails(tmp_path):
    (tmp_path / "paper.toml").write_text(
        "[paperforge]\ninstance_schema = 99\n[paper]\ntitle='x'\n")
    with pytest.raises(ConfigError):
        load_instance(tmp_path)


def test_local_overlay_wins(tmp_path):
    (tmp_path / "paper.toml").write_text(NEW_SHAPE)
    (tmp_path / ".paperforge.local.toml").write_text(
        '[build]\npretext_core_xsl = "/machine/core/pretext-html.xsl"\n')
    cfg = load_instance(tmp_path)
    assert str(cfg.pretext_core_xsl) == "/machine/core/pretext-html.xsl"


def test_path_resolution(tmp_path):
    assert resolve_instance_path(tmp_path, "a/b") == tmp_path / "a" / "b"
    assert resolve_instance_path(tmp_path, "/abs/x") == Path("/abs/x")
    home = resolve_instance_path(tmp_path, "~/y")
    assert home.is_absolute() and home == Path.home() / "y"


def test_state_derivation(tmp_path):
    (tmp_path / "paper.toml").write_text(NEW_SHAPE)
    cfg = load_instance(tmp_path)
    assert derive_state(cfg).name == "scaffolded"
    draft = tmp_path / "inputs/draft/main.tex"
    draft.parent.mkdir(parents=True)
    draft.write_text("x")
    assert derive_state(load_instance(tmp_path)).name == "ready-to-bootstrap"


# ---------------------------------------------------------------- init

def test_init_refuses_nonempty(tmp_path):
    (tmp_path / "occupied.txt").write_text("x")
    r = _pf("init", str(tmp_path), "--non-interactive", "--no-lean")
    assert r.returncode == 1 and "--force" in r.stderr


def test_init_scaffolds_clean(tmp_path):
    target = tmp_path / "inst"
    r = _pf("init", str(target), "--non-interactive", "--no-lean",
            "--slug", "mini")
    assert r.returncode == 0, r.stderr + r.stdout
    for rel in ("paper.toml", ".gitignore", "xsl/custom-html.xsl",
                "notation/notation-map.json", "references/extra-biblio.xml",
                "scripts/build-web.sh"):
        assert (target / rel).is_file(), rel
    for f in target.rglob("*"):
        if f.is_file() and f.suffix in (".xsl", ".sh", ".toml", ".ptx"):
            assert "@@" not in f.read_text(errors="ignore"), f
    json.load(open(target / "notation/notation-map.json"))
    cfg = load_instance(target)
    assert cfg.slug == "mini" and not cfg.formalizations
    # second run: refuses without --force, never overwrites with it
    before = (target / "paper.toml").read_text()
    assert _pf("init", str(target), "--non-interactive",
               "--no-lean").returncode == 1
    r = _pf("init", str(target), "--non-interactive", "--no-lean", "--force")
    assert r.returncode == 0
    assert (target / "paper.toml").read_text() == before


# ------------------------------------------------------------ converter

def test_tex2ptx_rewrites_and_profile(tmp_path):
    draft = tmp_path / "d.tex"
    draft.write_text(
        "\\documentclass{amsart}\n"
        "\\newtheorem{theorem}{Theorem}[section]\n"
        "\\newcommand{\\Mark}{\\emph{marked}}\n"
        "\\title{T}\\author{A}\n"
        "\\begin{document}\n\\maketitle\n"
        "\\section{One}\\label{sec:one}\nHello \\Mark{} world.\n"
        "\\end{document}\n")
    out = tmp_path / "src"
    base = [sys.executable, str(TOOL / "ingest" / "tex2ptx.py"), str(draft),
            "--out", str(out),
            "--numbering", str(tmp_path / "n.json")]
    r = subprocess.run(base + ["--rewrite", "\\Mark=meaningful"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    # 2 occurrences: the \newcommand definition line + the body use (the
    # definition is then dropped from the emitted macro block)
    assert "rewrite \\Mark -> meaningful (2 occurrence(s))" in r.stdout
    body = (out / "sec-one.ptx").read_text()
    assert "meaningful" in body and "\\Mark" not in body
    main = (out / "main.ptx").read_text()
    assert "\\Mark" not in main and "newcommand{meaningful}" not in main
    # document id defaults to the tex stem; --document-id overrides
    assert "<document-id>d</document-id>" in (out / "main.ptx").read_text()
    r = subprocess.run(base + ["--document-id", "my-doc"],
                       capture_output=True, text=True)
    assert "<document-id>my-doc</document-id>" in (out / "main.ptx").read_text()
    # unsupported numbering profile is refused
    r = subprocess.run(base + ["--numbering-profile", "chaotic"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "unsupported numbering profile" in r.stderr


def test_tex2ptx_tolerates_missing_maps(tmp_path):
    draft = tmp_path / "d.tex"
    draft.write_text(
        "\\documentclass{amsart}\n\\title{T}\\author{A}\n"
        "\\begin{document}\n\\section{One}\\label{sec:one}\nHi.\n"
        "\\end{document}\n")
    r = subprocess.run(
        [sys.executable, str(TOOL / "ingest" / "tex2ptx.py"), str(draft),
         "--out", str(tmp_path / "src"),
         "--numbering", str(tmp_path / "n.json"),
         "--lean-map", f"prim={tmp_path}/absent.json",
         "--notation-map", str(tmp_path / "absent-notation.json")],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "not present" in r.stdout


# ---------------------------------------------------------- postprocess

def test_site_assembly_is_portable_and_selective(tmp_path):
    from paperforge.postprocess import site as ppsite
    (tmp_path / "paper.toml").write_text(NEW_SHAPE)
    src = tmp_path / "web-assets" / "site"
    src.mkdir(parents=True)
    (src / "index.html").write_text("<h1>home</h1>")
    (src / ".DS_Store").write_bytes(b"\x00mac")
    (src / "._index.html").write_bytes(b"\x00appledouble")
    web = tmp_path / "output" / "web"
    web.mkdir(parents=True)
    (web / "paper.html").write_text("<p>paper</p>")

    warnings: list[str] = []
    ppsite.assemble(load_instance(tmp_path), warnings.append)
    site = tmp_path / "output" / "site"
    assert (site / "index.html").is_file()
    assert (site / "paper" / "paper.html").is_file()
    # macOS litter never reaches a web server
    assert not (site / ".DS_Store").exists()
    assert not (site / "._index.html").exists()
    # a missing PDF is named, not fatal
    assert any("paper.pdf" in w for w in warnings)

    # re-assembly is a clean rebuild, not an accumulation
    (site / "stale.html").write_text("x")
    ppsite.assemble(load_instance(tmp_path), warnings.append)
    assert not (site / "stale.html").exists()


def test_init_site_scaffold_does_not_recurse(tmp_path):
    """`--site` must never leave a scripts/build-site.sh that calls back
    into `paperforge build site` (that pair fork-bombs)."""
    target = tmp_path / "inst"
    assert _pf("init", str(target), "--non-interactive", "--no-lean",
               "--site").returncode == 0
    assert (target / "web-assets/site/index.html").is_file()
    script = target / "scripts" / "build-site.sh"
    if script.is_file():
        assert "paperforge build site" not in script.read_text()
    from paperforge.commands.build import _instance_site_script
    assert _instance_site_script(load_instance(target)) is None
    # a legacy shim left by an older init is ignored rather than re-entered
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("#!/bin/sh\nexec python3 -m paperforge build site .\n")
    assert _instance_site_script(load_instance(target)) is None


def test_postprocess_idempotent_and_honest(tmp_path):
    web = tmp_path / "web"
    js = web / "_static/pretext/js/mathjax_startup.js"
    js.parent.mkdir(parents=True)
    js.write_text('load: ["input/asciimath", "x"]')
    assert "1 patched" in ppweb.patch_mathjax_lazy(web)
    once = js.read_text()
    assert "already lazy" in ppweb.patch_mathjax_lazy(web)
    assert js.read_text() == once
    js.write_text("something entirely different")
    with pytest.raises(RuntimeError):
        ppweb.patch_mathjax_lazy(web)

    page = web / "paper.html"
    page.write_text('<div class="ptx-sidebar hidden">')
    assert "1 page(s) opened" in ppweb.open_toc_by_default(web)
    assert "1 already open" in ppweb.open_toc_by_default(web)

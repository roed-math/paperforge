"""The literal onboarding path against examples/minimal-paper, in a
directory whose path contains spaces (review §13.3). Bootstrap needs no
PreTeXt; the web build asserts only when `pretext` is installed."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1]
FIXTURE = TOOL / "examples" / "minimal-paper"


def pf(*args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(TOOL)
    return subprocess.run([sys.executable, "-m", "paperforge", *args],
                          cwd=cwd, capture_output=True, text=True, env=env)


@pytest.fixture()
def instance(tmp_path):
    root = tmp_path / "pf smoke" / "minimal paper"
    root.mkdir(parents=True)
    lean = tmp_path / "pf smoke" / "lean src"
    shutil.copytree(FIXTURE / "lean-src", lean)
    r = pf("init", ".", "--non-interactive",
           "--title", "A Minimal Fixture Paper", "--slug", "minimal",
           "--lean-root", "../lean src", "--lean-project-name",
           "minimal-lean", cwd=root)
    assert r.returncode == 0, r.stderr + r.stdout
    shutil.copyfile(FIXTURE / "draft.tex", root / "inputs/draft/main.tex")
    shutil.copyfile(FIXTURE / "notation-map.json",
                    root / "notation/notation-map.json")
    return root


def test_bootstrap_to_accept(instance):
    # build refuses before bootstrap, with an actionable message
    r = pf("build", "web", cwd=instance)
    assert r.returncode == 1 and "ingest --bootstrap" in r.stderr

    r = pf("ingest", "--bootstrap", cwd=instance)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "Bootstrap ingestion completed" in r.stdout

    numbering = json.load(open(instance / "crosswalk/numbering-current.json"))
    nums = {t: rec["number"] for t, rec in numbering["items"].items()}
    expected = json.load(open(FIXTURE / "expected/numbering-current.json"))
    assert nums == {t: rec["number"]
                    for t, rec in expected["items"].items()}

    cand = json.load(open(
        instance / "crosswalk/lean-decl-map.candidate.json"))
    exp = json.load(open(FIXTURE / "expected/lean-decl-map.candidate.json"))
    assert cand == exp

    # candidate is not silently promoted
    r = pf("build", "web", cwd=instance)
    assert r.returncode == 1 and "accept lean-decl-map" in r.stderr

    r = pf("accept", "lean-decl-map", cwd=instance)
    assert r.returncode == 0, r.stderr
    assert (instance / "crosswalk/lean-decl-map.json").is_file()

    r = pf("status", cwd=instance)
    assert "buildable" in r.stdout


def test_bootstrap_without_lean(tmp_path):
    root = tmp_path / "no lean"
    root.mkdir()
    r = pf("init", ".", "--non-interactive", "--no-lean", cwd=root)
    assert r.returncode == 0, r.stderr + r.stdout
    shutil.copyfile(FIXTURE / "draft.tex", root / "inputs/draft/main.tex")
    r = pf("ingest", "--bootstrap", cwd=root)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "paperforge build web" in r.stdout


@pytest.mark.skipif(shutil.which("pretext") is None,
                    reason="pretext not installed")
def test_build_web(instance):
    assert pf("ingest", "--bootstrap", cwd=instance).returncode == 0
    assert pf("accept", "lean-decl-map", cwd=instance).returncode == 0
    r = pf("build", "web", cwd=instance)
    assert r.returncode == 0, r.stderr + r.stdout
    web = instance / "output/web"
    page = web / "paper.html"
    assert page.is_file()
    html = page.read_text()
    assert "lean-link" in html                     # badges resolved
    assert (web / "detail-ui.js").is_file()        # UI bundle assembled
    prov = json.load(open(instance / "output/build-provenance.json"))
    assert prov["instance"]["schema"] == 1
    # validators run and report the fixture's REAL findings
    r = pf("check", cwd=instance)
    assert r.returncode == 1
    assert "section_summaries" in r.stdout
    assert "notation_order" in r.stdout

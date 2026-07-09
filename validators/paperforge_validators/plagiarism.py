"""Requirement 3: flag verbatim overlap between the paper's prose and the
cited literature. See ../../docs/PLAGIARISM.md.

Mechanics: build an n-word shingle index over the *external sources* (the PDFs
/texts under ``[plagiarism] sources``, typically ``references/``); walk the
assembled document's prose (math, code, bibliography entries, and attributed
quotes excluded — see _document.iter_prose); report every maximal run of >= n
consecutive words that appears verbatim in a source.

Severity: runs of >= ``error_run`` words (default 12) are errors; shorter
matches are warnings (stock mathematical phrases live in the 7-10 word range;
they still deserve a human glance but rarely need rewriting).

Provenance: the AI draft (``[inputs] ai_draft``) is NOT a flag-source — the
paper legitimately derives from it. It is the *provenance baseline*: findings
are labeled ``inherited-from-draft`` (the AI draft already contained the
overlapping text — the LLM that wrote the draft copied the literature) or
``pipeline-added`` (the overlap entered during our processing and is ours to
fix). Both are reported; responsibility differs.

Config (``[plagiarism]``): ``ngram`` (default 7), ``error_run`` (12),
``sources`` (default ["references/"]), ``max_findings`` in the console report
(25; the full report always goes to ``report_json``, default
``output/plagiarism-report.json``).

Reports only; never edits. Stage 2 remains a human read.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import Finding, instance_root
from ._document import iter_prose, load_assembled

_WORD = re.compile(r"[a-z][a-z'’-]*")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _shingles(tokens: list[str], n: int) -> set[int]:
    return {hash(tuple(tokens[i:i + n])) for i in range(len(tokens) - n + 1)}


def _detex(tex: str) -> str:
    """Crude LaTeX -> prose for the provenance baseline (labels only)."""
    tex = re.sub(r"(?<!\\)%.*", " ", tex)
    tex = re.sub(r"\\begin\{(equation|align|gather|multline)\*?\}.*?"
                 r"\\end\{\1\*?\}", " ", tex, flags=re.S)
    tex = re.sub(r"\$\$?[^$]*\$\$?", " ", tex)
    tex = re.sub(r"\\\[.*?\\\]", " ", tex, flags=re.S)
    tex = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", tex)
    return tex.replace("{", " ").replace("}", " ").replace("~", " ")


def _extract_source_text(path: Path, cache_dir: Path) -> str | None:
    if path.suffix.lower() in (".txt", ".md"):
        return path.read_text(errors="ignore")
    if path.suffix.lower() == ".tex":
        return _detex(path.read_text(errors="ignore"))
    if path.suffix.lower() == ".pdf":
        if not shutil.which("pdftotext"):
            return None
        cache = cache_dir / f"{path.stem}.{int(path.stat().st_mtime)}.txt"
        if cache.exists():
            return cache.read_text(errors="ignore")
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["pdftotext", "-q", str(path), str(cache)],
                           check=True, timeout=120)
        except Exception:
            return None
        return cache.read_text(errors="ignore")
    return None


def _source_files(root: Path, sources: list[str]):
    for s in sources:
        p = (root / s) if not Path(s).is_absolute() else Path(s)
        if p.is_dir():
            yield from sorted(q for q in p.rglob("*")
                              if q.suffix.lower() in (".pdf", ".txt", ".md", ".tex"))
        elif p.exists():
            yield p


def check(config: dict) -> list[Finding]:
    root = instance_root(config)
    cfg = config.get("plagiarism", {})
    n = int(cfg.get("ngram", 7))
    error_run = int(cfg.get("error_run", 12))
    max_findings = int(cfg.get("max_findings", 25))
    sources = cfg.get("sources", ["references/"])
    report_path = root / cfg.get("report_json", "output/plagiarism-report.json")
    cache_dir = root / ".cache" / "paperforge"

    findings: list[Finding] = []

    # --- index external sources ---
    index: dict[str, set[int]] = {}
    for f in _source_files(root, sources):
        text = _extract_source_text(f, cache_dir)
        if text is None:
            findings.append(Finding("plagiarism", "warning",
                                    f"could not extract text from {f.name} "
                                    f"(pdftotext missing or failed)"))
            continue
        toks = _tokens(text)
        if len(toks) >= n:
            index[f.name] = _shingles(toks, n)
    if not index:
        findings.append(Finding("plagiarism", "warning",
                                "no readable sources configured — check skipped"))
        return findings

    # --- provenance baseline (the AI draft) ---
    draft_shingles: set[int] = set()
    draft_rel = config.get("inputs", {}).get("ai_draft")
    if draft_rel and (root / draft_rel).exists():
        draft_shingles = _shingles(_tokens(_detex(
            (root / draft_rel).read_text(errors="ignore"))), n)

    # --- document prose, tokenized with location tracking ---
    try:
        prose = iter_prose(load_assembled(config))
    except Exception as e:
        return [Finding("plagiarism", "error", f"cannot assemble source: {e}")]
    doc_toks: list[str] = []
    tok_loc: list[str] = []
    for text, loc in prose:
        ts = _tokens(text)
        doc_toks.extend(ts)
        tok_loc.extend([loc] * len(ts))

    # --- scan: maximal runs of shingle hits, per source ---
    all_hits = []   # (length, start, source)
    for src, sh in index.items():
        i, N = 0, len(doc_toks) - n + 1
        while i < N:
            if hash(tuple(doc_toks[i:i + n])) in sh:
                j = i
                while j + 1 < N and hash(tuple(doc_toks[j + 1:j + 1 + n])) in sh:
                    j += 1
                all_hits.append((j - i + n, i, src))
                i = j + n
            else:
                i += 1

    # --- dedupe identical spans, build findings ---
    seen_excerpts: dict[str, int] = {}
    detailed = []
    for length, start, src in sorted(all_hits, reverse=True):
        words = doc_toks[start:start + length]
        excerpt = " ".join(words[:15]) + ("…" if length > 15 else "")
        if excerpt in seen_excerpts:
            seen_excerpts[excerpt] += 1
            continue
        seen_excerpts[excerpt] = 1
        inherited = hash(tuple(words[:n])) in draft_shingles
        detailed.append({
            "words": length, "excerpt": excerpt, "source": src,
            "location": tok_loc[start],
            "provenance": "inherited-from-draft" if inherited else "pipeline-added",
        })
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(
        {"ngram": n, "sources": sorted(index), "findings": detailed}, indent=1))

    for d in detailed[:max_findings]:
        sev = "error" if d["words"] >= error_run else "warning"
        findings.append(Finding(
            "plagiarism", sev,
            f'{d["words"]}-word overlap with {d["source"]} '
            f'({d["provenance"]}): "{d["excerpt"]}"', d["location"]))
    if len(detailed) > max_findings:
        findings.append(Finding(
            "plagiarism", "warning",
            f"{len(detailed) - max_findings} further overlap(s) in "
            f"{report_path.relative_to(root)}"))
    return findings

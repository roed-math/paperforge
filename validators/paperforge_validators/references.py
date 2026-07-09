"""Requirement 10 + the references framework (docs/REFERENCES.md).

Four deterministic checks:

  1. unused bibliography entries (math convention: every entry is cited);
  2. dangling citations (<xref ref="bib-K"> with no <biblio xml:id="bib-K">);
  3. axiom coverage — every Lean axiom (crosswalk/axiom-citations.json, from
     ingest/lean_axioms.py) must (a) carry a literature citation in its
     docstring [warn: formalization-side gap], (b) have each cited work
     resolvable to a bibliography entry via references/bib-aliases.json
     [error: the paper's bibliography lacks a work the formalization rests
     on], and (c) have its paper-anchor blocks' enclosing division contain a
     citation to that work [error: the paper states the fact without citing];
  4. pin verification (stage 1) — a citation pin like
     ``[<xref ref="bib-Labute"/>, Theorem 8]`` must have its number tokens
     present in the cited work's local PDF text [warning]. Narrows the human
     stage-2 read; never replaces it.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import Finding, instance_root
from ._document import XML_ID, load_assembled, _localname

_PIN_NUM = re.compile(r"\d+(?:\.\d+)*|\b[IVXLC]{1,6}\b")


def _pdf_text(pdf: Path, cache_dir: Path) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    cache = cache_dir / f"{pdf.stem}.{int(pdf.stat().st_mtime)}.txt"
    if not cache.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["pdftotext", "-q", str(pdf), str(cache)],
                           check=True, timeout=120)
        except Exception:
            return None
    return cache.read_text(errors="ignore")


def _bib_pdf_map(bib_texts: dict[str, str], pdf_dir: Path) -> dict[str, Path]:
    """bib key -> local PDF, by surname-token overlap with the filename."""
    pdfs = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    out = {}
    for key, text in bib_texts.items():
        toks = {t.lower() for t in re.findall(r"[A-Z][a-z]{3,}", text)}
        best, score = None, 0
        for p in pdfs:
            ftoks = {t.lower() for t in re.findall(r"[A-Za-z]{4,}", p.stem)}
            s = len(toks & ftoks)
            if s > score:
                best, score = p, s
        if best is not None and score >= 2:
            out[key] = best
    return out


def check(config: dict) -> list[Finding]:
    root = instance_root(config)
    findings: list[Finding] = []
    try:
        doc = load_assembled(config)
    except Exception as e:
        return [Finding("references", "error", f"cannot assemble source: {e}")]

    # --- collect bibliography and citations ---
    bib_texts: dict[str, str] = {}
    for b in doc.iter("biblio"):
        xid = b.get(XML_ID)
        if xid:
            bib_texts[xid] = " ".join(b.itertext())
    cites: dict[str, list[str]] = {}          # bib key -> [division tag]
    pins: list[tuple[str, str, str]] = []     # (bib key, pin text, division)

    div_of: dict = {}

    def division_of(el) -> str:
        for anc in [el] + list(el.iterancestors()):
            if isinstance(anc.tag, str) and _localname(anc) in (
                    "section", "subsection", "appendix") and anc.get(XML_ID):
                return anc.get(XML_ID)
        return "document"

    for x in doc.iter("xref"):
        ref = x.get("ref", "")
        if not ref.startswith("bib-"):
            continue
        div = division_of(x)
        cites.setdefault(ref, []).append(div)
        tail = (x.tail or "")
        if tail.startswith(","):
            pin = tail[1:].split("]")[0].strip()
            if pin:
                pins.append((ref, pin, div))

    # --- 1. unused entries / 2. dangling citations ---
    for key in sorted(set(bib_texts) - set(cites)):
        findings.append(Finding(
            "references", "error",
            f"bibliography entry '{key}' is never cited in the text "
            f"(math convention: remove it or cite it)", key))
    for key in sorted(set(cites) - set(bib_texts)):
        findings.append(Finding(
            "references", "error",
            f"citation to '{key}' has no bibliography entry", key))

    # --- 3. axiom coverage ---
    ax_path = root / "crosswalk" / "axiom-citations.json"
    aliases_path = root / "references" / "bib-aliases.json"
    aliases = json.load(open(aliases_path)) if aliases_path.exists() else {}
    if ax_path.exists():
        axioms = json.load(open(ax_path))
        # division of each paper tag, and citations present per division
        tag_div: dict[str, str] = {}
        for el in doc.iter():
            if isinstance(el.tag, str) and el.get(XML_ID):
                tag_div[el.get(XML_ID)] = division_of(el)
        cited_in_div: dict[str, set] = {}
        for key, divs in cites.items():
            for d in divs:
                cited_in_div.setdefault(d, set()).add(key)
        for name, ax in axioms.items():
            short = name.rsplit(".", 1)[-1]
            label = ax.get("census") or short
            if not ax["works"]:
                findings.append(Finding(
                    "references", "warning",
                    f"axiom {label} ({short}) has no parsed Citation: line in "
                    f"its docstring — formalization-side gap", ax["file"]))
                continue
            bib_keys = {aliases.get(w) for w in ax["works"]}
            missing = [w for w in ax["works"] if not aliases.get(w)]
            for w in missing:
                findings.append(Finding(
                    "references", "warning",
                    f"axiom {label} cites '{w}', which maps to no bibliography "
                    f"entry (bib-aliases.json) — the paper may be missing a "
                    f"work the formalization rests on", short))
            bib_keys.discard(None)
            if not ax["paper_tags"]:
                findings.append(Finding(
                    "references", "warning",
                    f"axiom {label} has no resolvable Paper: anchor — cannot "
                    f"check paper-side citation placement", short))
                continue
            for tag in ax["paper_tags"]:
                div = tag_div.get(tag)
                if div is None:
                    findings.append(Finding(
                        "references", "warning",
                        f"axiom {label}: paper anchor '{tag}' not found in "
                        f"the assembled document", short))
                    continue
                if bib_keys and not (bib_keys & cited_in_div.get(div, set())):
                    # equation-number anchors resolve through CURRENT numbering
                    # only (no old-snapshot eq map until the v428 tex exists),
                    # so they may be drift victims: downgrade to warning.
                    eq_anchor = tag.startswith("eq-")
                    findings.append(Finding(
                        "references", "warning" if eq_anchor else "error",
                        f"axiom {label} ({short}) anchors at '{tag}' but its "
                        f"division '{div}' cites none of "
                        f"{sorted(k or '?' for k in bib_keys)}"
                        + (" [eq anchor — verify against v428 numbering]"
                           if eq_anchor else
                           " — the paper rests on this fact there without citing it"),
                        tag))

    # --- 4. pin verification against local PDFs ---
    pdf_dir = root / config.get("references", {}).get("pdf_dir", "references/")
    cache_dir = root / ".cache" / "paperforge"
    bib_pdf = _bib_pdf_map(bib_texts, pdf_dir)
    for key, pin, div in pins:
        pdf = bib_pdf.get(key)
        if pdf is None:
            findings.append(Finding(
                "references", "warning",
                f"pin '[{key}, {pin}]' — no local PDF matched to '{key}'; "
                f"cannot verify", div))
            continue
        text = _pdf_text(pdf, cache_dir)
        if text is None:
            continue
        toks = _PIN_NUM.findall(pin)
        missing = [t for t in toks if t not in text]
        if missing:
            findings.append(Finding(
                "references", "warning",
                f"pin '[{key}, {pin}]': token(s) {missing} not found in "
                f"{pdf.name} — verify by hand (stage 2)", div))
    return findings

#!/usr/bin/env python3
"""lean_citable: rank formalization nodes by likelihood of being CITABLE —
i.e. corresponding to known mathematics in the literature rather than to the
paper's novel contribution or to encoding glue.

Motivation (see the design discussion in docs/REFERENCES.md): the axiom census
has perfect precision but shrinking recall as axioms are discharged; the
citation-preserving-discharge convention keeps those, but known mathematics
that was *never* an axiom (proved in-repo from Mathlib, e.g. a Hopfian
property, cohomological toolkit lemmas) is invisible to it. This funnel
surfaces candidates for an LLM matching pass whose decisions are cached in
``references/formalized-known.json``.

Signals (cheap, structural — the LLM pass does the actual literature match):
  + docstring names a known work / classical-fact phrasing
  + classical-topic file (Foundations/, Shapiro, Corestriction, Kummer, ...)
  + classical vocabulary in the statement signature
  + theorem/lemma kind, substantial docstring
  - paper-native vocabulary in the signature (the paper's own objects)
  - glue-shaped names (_apply/_mk/_coe/...), instances
Census-covered declarations (axiom-citations.json) are excluded — they are
already handled with human-curated citations.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

PAPER_NATIVE = re.compile(
    r"GammaA|[Aa]dmissible|[Ff]ramed|BoundaryData|[Ee]xactImage|"
    r"[Mm]arkedQuotient|candidateR|eGamma|orbitDatum|OrbitData|FactorSet|"
    r"RStage|stageR|wordLedger|WordLedger|fullMarking|deepSES|deepPart|DeepPart")
CLASSICAL_SIG = re.compile(
    r"AbsGalQ2|absGal|Demushkin|[Hh]ilbert|[Kk]ummer|[Rr]eciprocity|"
    r"[Tt]ameQuotient|tameF|UnitFiltration|unitFiltration|cyclotomic|Cyclotomic|"
    r"Euler|Arf|[Ee]vens|Shapiro|shapiro|[Cc]orestrict|[Tt]ransgress|Frattini|"
    r"[Hh]opfian|[Pp]rofinite|maxProP|Frobenius|H[012] |cohomolog|ContinuousMulEquiv|"
    r"IntermediateField|ℚ_\[2\]|ZMod 2|Gal\b")
DOC_WORKS = re.compile(
    r"NSW|Serre|Labute|Neukirch|Milne|Brown\b|Evens|Kahn|Kozlowski|Ribes|"
    r"Zalesski|RZ\b|Stix|Iwasawa|Jannsen|Wingberg|Washington|Fesenko|O'Meara")
DOC_CLASSICAL = re.compile(
    r"classical|standard|well[- ]known|textbook|folklore|literature|"
    r"Mathlib lacks|not (?:yet )?in Mathlib", re.I)
GLUE_NAME = re.compile(
    r"_(apply|mk|coe|def|symm|comm|assoc|left|right|fst|snd|inj|congr|ext|"
    r"cast|val|toFun|of[A-Z]\w*)$|[Aa]ux|helper|'$")
CLASSICAL_FILES = re.compile(
    r"Foundations|Shapiro|Corestriction|Transgression|Kummer|UnitFiltration|"
    r"Demushkin|HilbertSymbol|EulerCharacteristic|Reciprocity|TameQuotient|"
    r"MaxProP|Reconstruction|Orientation|DyadicPresentation|Cochains|"
    r"QuadraticF|GaussSum|Corestrict")


def load_declmap():
    path = Path(__file__).resolve().parent / "lean_declmap.py"
    spec = importlib.util.spec_from_file_location("pf_declmap", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pf_declmap"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lean_root", type=Path)
    ap.add_argument("--census", type=Path,
                    help="axiom-citations.json (these decls are excluded)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args()

    covered = set()
    if args.census and args.census.exists():
        covered = set(json.load(open(args.census)))

    dm = load_declmap()
    lines_cache: dict[str, list[str]] = {}

    def context(f: str, ln: int, n: int = 5) -> str:
        if f not in lines_cache:
            lines_cache[f] = Path(f).read_text(errors="ignore").splitlines()
        return "\n".join(lines_cache[f][ln - 1:ln - 1 + n])

    rows = []
    for full, doc, f, ln, _private, _kind in dm.iter_decls(args.lean_root):
        if full in covered or full.rsplit(".", 1)[-1] in {
                n.rsplit(".", 1)[-1] for n in covered}:
            continue
        sig = context(str(f), ln)
        kind = sig.split()[0] if sig.split() else "?"
        doc = doc or ""
        score = 0
        signals = []
        if PAPER_NATIVE.search(sig):
            score -= 4; signals.append("paper-native-sig")
        if CLASSICAL_SIG.search(sig):
            score += 2; signals.append("classical-sig")
        if CLASSICAL_FILES.search(str(f)):
            score += 2; signals.append("classical-file")
        if DOC_WORKS.search(doc):
            score += 3; signals.append("doc-names-work")
        if DOC_CLASSICAL.search(doc):
            score += 2; signals.append("doc-classical-phrase")
        if GLUE_NAME.search(full):
            score -= 2; signals.append("glue-name")
        if kind in ("theorem", "lemma"):
            score += 1
        elif kind in ("instance",):
            score -= 2; signals.append("instance")
        elif kind in ("def", "abbrev", "structure"):
            score -= 1
        if len(doc) > 200:
            score += 1; signals.append("documented")
        if score >= 3:
            rows.append({
                "decl": full, "kind": kind, "score": score,
                "signals": signals,
                "file": str(Path(f).relative_to(args.lean_root)), "line": ln,
                "sig": sig[:300],
                "doc": doc[:600],
            })
    rows.sort(key=lambda r: -r["score"])
    args.out.write_text(json.dumps(rows[:args.top], indent=1))
    print(f"{len(rows)} candidates scored >= 3; wrote top {min(args.top, len(rows))} "
          f"to {args.out}")
    hist = {}
    for r in rows:
        hist[r["score"]] = hist.get(r["score"], 0) + 1
    print("score histogram:", dict(sorted(hist.items(), reverse=True)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

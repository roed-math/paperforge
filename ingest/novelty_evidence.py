#!/usr/bin/env python3
"""novelty_evidence: deterministic evidence collection for the novelty dossier
(docs/NOVELTY.md). Emits novelty/evidence.json with five seed families:

  novel_defs      class-4 seeds: novel definitions/structures with signature
                  genericity (instance-constant mentions) and atlas fan-in
  contrast_lang   class-2 seeds: the paper's own contrast language, by block
  census_events   class-2/3 seeds: axioms discharged / hypothesis notes from
                  the Lean census artifact
  import_profile  class-5 seeds: Mathlib import-area histogram
  method_units    class-1 seeds: section/subsection titles + Lean module-doc
                  headlines (## lines of /-! blocks)

Everything is keyed by stable ids (decl names, block tags) so the LLM pass
can be incremental.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

INSTANCE_CONSTANTS = re.compile(
    r"ℚ_\[2\]|AbsGalQ2|absGalQ2|AlgebraicClosure ℚ|Q2|ℤ_\[2\]")
CONTRAST = re.compile(
    r"exceptional|in contrast|by contrast|unlike|resisted|surprising|"
    r"unexpectedly?|fails?\b|cannot\b|not integral|breaks down|obstruction|"
    r"separate argument|no longer|does not (?:apply|extend|hold)", re.I)
MODULE_HEAD = re.compile(r"/-!\s*##+\s*([^\n]+)")


def load_declmap():
    path = Path(__file__).resolve().parent / "lean_declmap.py"
    spec = importlib.util.spec_from_file_location("pf_declmap2", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pf_declmap2"] = mod
    spec.loader.exec_module(mod)
    return mod


def collect_novel_defs(lean_root: Path, known_path: Path, atlas_path: Path):
    """Class-4 seeds: novel defs/structures, genericity + fan-in."""
    known = {}
    if known_path.exists():
        known = json.load(open(known_path)).get("decisions", {})
    fan_in: Counter = Counter()
    if atlas_path.exists():
        g = json.load(open(atlas_path))
        for e in g.get("edges", []):
            # edge source depends on target -> target gains fan-in
            tgt = e.get("to") or e.get("target")
            if tgt:
                fan_in[tgt] += 1
    dm = load_declmap()
    lines_cache: dict[str, list[str]] = {}

    def sig(f, ln, n=4):
        if f not in lines_cache:
            lines_cache[f] = Path(f).read_text(errors="ignore").splitlines()
        return " ".join(lines_cache[f][ln - 1:ln - 1 + n])

    out = []
    for full, doc, f, ln in dm.iter_decls(lean_root):
        s = sig(str(f), ln)
        kind = s.split()[0] if s.split() else "?"
        if kind not in ("def", "structure", "abbrev"):
            continue
        status = known.get(full, {}).get("status")
        if status and status.startswith("known"):
            continue
        generic = not INSTANCE_CONSTANTS.search(s)
        fi = fan_in.get(full, 0) or fan_in.get(full.rsplit(".", 1)[-1], 0)
        if generic and (fi >= 5 or (doc and len(doc) > 150)):
            out.append({"decl": full, "kind": kind, "fan_in": fi,
                        "generic_signature": generic,
                        "file": str(Path(f).relative_to(lean_root)), "line": ln,
                        "doc": (doc or "")[:300]})
    out.sort(key=lambda r: -r["fan_in"])
    return out[:40]


def collect_contrast(source_dir: Path):
    """Class-2 seeds: contrast language in the paper, by nearest block tag."""
    out = []
    for f in sorted(source_dir.glob("*.ptx")):
        text = f.read_text()
        ids = [(m.start(), m.group(1))
               for m in re.finditer(r'xml:id="([^"]+)"', text)]
        for m in CONTRAST.finditer(text):
            tag = "?"
            for pos, xid in ids:
                if pos < m.start():
                    tag = xid
                else:
                    break
            ctx = " ".join(text[max(0, m.start() - 120):m.end() + 120].split())
            out.append({"block": tag, "match": m.group(0), "context": ctx,
                        "file": f.name})
    return out


def collect_census_events(census_path: Path):
    """Class-2/3 seeds from the axiom census artifact."""
    if not census_path.exists():
        return []
    axioms = json.load(open(census_path))
    events = []
    for name, ax in axioms.items():
        if ax.get("status") == "discharged":
            events.append({"event": "axiom-discharged", "decl": name,
                           "census": ax.get("census"),
                           "note": "expected classical input turned out "
                                   "provable from Mathlib + this repo"})
    return events


def collect_import_profile(lean_root: Path):
    """Class-5 seeds: which Mathlib areas the formalization stands on."""
    hist: Counter = Counter()
    for f in lean_root.rglob("*.lean"):
        if ".lake" in f.parts:
            continue
        for m in re.finditer(r"^import\s+Mathlib\.(\w+)\.(\w+)",
                             f.read_text(errors="ignore"), re.M):
            hist[f"{m.group(1)}.{m.group(2)}"] += 1
    return dict(hist.most_common(30))


def collect_method_units(source_dir: Path, lean_root: Path, numbering: Path):
    """Class-1 seeds: division titles + Lean module headlines."""
    units = []
    if numbering.exists():
        items = json.load(open(numbering))["items"]
        for tag, r in items.items():
            if r["kind"] in ("section", "subsection", "appendix"):
                units.append({"kind": "division", "id": tag,
                              "number": r["number"]})
    for f in sorted(lean_root.rglob("*.lean")):
        if ".lake" in f.parts:
            continue
        for m in MODULE_HEAD.finditer(f.read_text(errors="ignore")):
            units.append({"kind": "module-head", "id": str(f.name),
                          "title": m.group(1).strip()[:100]})
    return units


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", type=Path, nargs="?", default=Path.cwd())
    ap.add_argument("--lean-root", type=Path, required=True)
    ap.add_argument("--atlas", type=Path, help="atlas-graph.json (fan-in)")
    args = ap.parse_args()
    root = args.instance

    ev = {
        "novel_defs": collect_novel_defs(
            args.lean_root, root / "references" / "formalized-known.json",
            args.atlas or Path("/nonexistent")),
        "contrast_lang": collect_contrast(root / "source"),
        "census_events": collect_census_events(
            root / "crosswalk" / "axiom-citations.json"),
        "import_profile": collect_import_profile(args.lean_root),
        "method_units": collect_method_units(
            root / "source", args.lean_root,
            root / "crosswalk" / "numbering-current.json"),
    }
    out = root / "novelty" / "evidence.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(ev, indent=1))
    print(f"wrote {out}: "
          + ", ".join(f"{k}={len(v) if isinstance(v, list) else len(v)}"
                      for k, v in ev.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

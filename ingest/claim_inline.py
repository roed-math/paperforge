#!/usr/bin/env python3
"""claim_inline: convert claim-statement LaTeX to PreTeXt inline markup.

Novelty-claim statements (and new_refs bibliography entries) are authored in
inline LaTeX — the dialect mathematicians actually write: ``$...$`` math,
``\\cite[pin]{KEY}``, ``\\emph{}``, ``\\texttt{}``, ``--``/``---``. This is
the deterministic render helper the intro-novelty pass uses: it reuses
tex2ptx.convert_inline (the same converter that ingests the whole paper), so
claim rendering can never diverge from paper rendering.

    echo 'rigidity \\cite[Section 2.5]{RZ} for $P$' | python3 claim_inline.py
    -> rigidity [<xref ref="bib-RZ"/>, Section 2.5] for <m>P</m>

    python3 claim_inline.py --biblio 'F. Author, \\emph{Title}, 2020.' --key bib-X
    -> <biblio type="raw" xml:id="bib-X"> ... </biblio>
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def load_tex2ptx():
    path = Path(__file__).resolve().parent / "tex2ptx.py"
    spec = importlib.util.spec_from_file_location("pf_tex2ptx", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pf_tex2ptx"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_labels(numbering: Path | None) -> set[str]:
    r"""Real labels from the instance's numbering database, so \cref in a
    claim validates against the paper (unknown labels warn on stderr)."""
    import json
    path = numbering or Path.cwd() / "crosswalk" / "numbering-current.json"
    if not path.exists():
        return set()
    items = json.load(open(path))["items"]
    return {r["label"] for r in items.values() if r.get("label")}


def convert(latex: str, numbering: Path | None = None) -> str:
    t2p = load_tex2ptx()
    refs = t2p.RefMap(load_labels(numbering))
    return t2p.convert_inline(latex.strip(), refs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--biblio", help="convert a bibliography entry instead of "
                                     "reading statement LaTeX from stdin")
    ap.add_argument("--key", help="xml:id for --biblio output")
    ap.add_argument("--numbering", type=Path,
                    help="numbering-current.json (default: ./crosswalk/...)")
    args = ap.parse_args()
    if args.biblio:
        inner = convert(args.biblio, args.numbering)
        key = args.key or "bib-FIXME"
        print(f'<biblio type="raw" xml:id="{key}">\n  {inner}\n  </biblio>')
    else:
        print(convert(sys.stdin.read(), args.numbering))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

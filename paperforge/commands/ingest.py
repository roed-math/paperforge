"""paperforge ingest: draft -> generated PreTeXt (+ numbering, source map).

Normal mode uses the accepted sidecars and declaration maps and fails
actionably when an accepted map is missing but a candidate exists.

--bootstrap is the first-run path (review §5-P0): ingest WITHOUT any
declaration map, produce the current numbering, then mine one CANDIDATE
map per configured formalization and stop at the review boundary — the
heuristic output is never silently promoted (see `paperforge accept`).
"""
from __future__ import annotations

from ..config import ConfigError
from ..state import candidate_declmap
from . import _stages as st
from ._common import add_instance_arg, fail, load


def add_parser(sub) -> None:
    p = sub.add_parser("ingest", help="convert the draft to generated PreTeXt")
    add_instance_arg(p)
    p.add_argument("--bootstrap", action="store_true",
                   help="first run: no declaration maps required; generates "
                        "candidates and stops at the review boundary")
    p.set_defaults(func=run)


def run(args, extra) -> int:
    try:
        cfg = load(args)
    except ConfigError as e:
        return fail(str(e))
    if not cfg.draft.is_file():
        return fail(f"draft not found at {cfg.draft} — put the LaTeX draft "
                    f"in place (paper.toml [inputs] ai_draft)")

    if not args.bootstrap:
        for fm in cfg.formalizations:
            if not fm.declmap.is_file():
                cand = candidate_declmap(fm.declmap)
                hint = (f"a candidate exists at {cand.relative_to(cfg.root)} — "
                        f"review it, then: paperforge accept lean-decl-map"
                        + (f" --formalization {fm.name}" if not fm.primary
                           else "")) if cand.is_file() else \
                       "run `paperforge ingest --bootstrap` to generate one"
                return fail(
                    f"no accepted declaration map for formalization "
                    f"{fm.name!r} at {fm.declmap.relative_to(cfg.root)}.\n"
                    f"{hint}\n"
                    f"(or remove the formalization from paper.toml to build "
                    f"without badges)")

    r = st.Runner()
    try:
        cfg_has_trust = bool(cfg.raw.get("trust_table"))
        r.run("trust table", lambda: st.trust_table(cfg),
              skip=None if cfg_has_trust else "not configured")
        r.run("ingest draft",
              lambda: st.tex2ptx(cfg, bootstrap=args.bootstrap))
        r.run("author metadata", lambda: st.author_metadata(cfg))
        if args.bootstrap and cfg.formalizations:
            def gen_candidates() -> str:
                made = st.bootstrap_declmaps(cfg)
                return f"{len(made)} candidate map(s)"
            r.run("candidate decl maps", gen_candidates)
    except st.StageError as e:
        return fail(str(e))

    if args.bootstrap:
        print("\nBootstrap ingestion completed.")
        print("Created:")
        print("  crosswalk/numbering-current.json")
        for fm in cfg.formalizations:
            print(f"  {candidate_declmap(fm.declmap).relative_to(cfg.root)}")
        if cfg.formalizations:
            print("\nReview the candidate declaration map(s), then:")
            print("  paperforge accept lean-decl-map"
                  + ("" if len(cfg.formalizations) == 1
                     else "   (--formalization NAME for the others)"))
            print("  paperforge build web")
        else:
            print("\nNext: paperforge build web")
    return 0

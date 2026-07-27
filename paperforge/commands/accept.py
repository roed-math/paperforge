"""paperforge accept: deliberately promote a reviewed candidate artifact.

Bootstrap generates crosswalk/lean-decl-map.candidate.json (heuristic —
its mining is name/docstring matching and its own docs say the output must
be reviewed). Acceptance is an explicit copy, never silent.
"""
from __future__ import annotations

import shutil

from ..config import ConfigError
from ..state import candidate_declmap
from ._common import add_instance_arg, fail, load


def add_parser(sub) -> None:
    p = sub.add_parser("accept",
                       help="promote a reviewed candidate artifact")
    p.add_argument("artifact", choices=["lean-decl-map"],
                   help="which candidate to accept")
    add_instance_arg(p)
    p.add_argument("--formalization", default=None, metavar="NAME",
                   help="which project's map (default: the primary)")
    p.add_argument("--force", action="store_true",
                   help="overwrite an existing accepted map")
    p.set_defaults(func=run)


def run(args, extra) -> int:
    try:
        cfg = load(args)
    except ConfigError as e:
        return fail(str(e))
    fm = cfg.formalization(args.formalization)
    if fm is None:
        return fail("no formalization configured"
                    + (f" named {args.formalization!r}" if args.formalization
                       else ""))
    cand = candidate_declmap(fm.declmap)
    if not cand.is_file():
        return fail(f"no candidate at {cand} — run `paperforge ingest "
                    f"--bootstrap` first")
    if fm.declmap.is_file() and not args.force:
        return fail(f"accepted map already exists at {fm.declmap} — "
                    f"pass --force to replace it with the candidate")
    shutil.copyfile(cand, fm.declmap)
    print(f"accepted: {cand.name} -> {fm.declmap.relative_to(cfg.root)}")
    print("next: paperforge build web   (badges now resolve against it)")
    return 0

"""paperforge status: the derived bootstrap/build state and the next command."""
from __future__ import annotations

from ..config import ConfigError
from ..state import candidate_declmap, derive_state
from ._common import add_instance_arg, fail, load


def add_parser(sub) -> None:
    p = sub.add_parser("status", help="derived instance state + next command")
    add_instance_arg(p)
    p.set_defaults(func=run)


def run(args, extra) -> int:
    try:
        cfg = load(args)
    except ConfigError as e:
        print("State: uninitialized")
        return fail(str(e))
    st = derive_state(cfg)
    print(f"State: {st.name}")
    print(f"  {st.detail}")
    rows = []
    numbering = cfg.root / "crosswalk" / "numbering-current.json"
    rows.append((numbering, "current numbering"))
    for fm in cfg.formalizations:
        rows.append((fm.declmap, f"accepted decl map ({fm.name})"))
        if not fm.declmap.is_file():
            rows.append((candidate_declmap(fm.declmap),
                         f"candidate decl map ({fm.name})"))
    present = [f"  {d} ({p.relative_to(cfg.root)})" for p, d in rows if p.is_file()]
    missing = [f"  {d} ({p.relative_to(cfg.root)})" for p, d in rows if not p.is_file()]
    if present:
        print("Present:")
        print("\n".join(present))
    if missing:
        print("Missing:")
        print("\n".join(missing))
    print(f"Next: {st.next_command}")
    return 0

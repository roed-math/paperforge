"""paperforge migrate config: report old-shape keys and the normalized
equivalent. --check only for now: it prints the deprecations and the
proposed [formalizations.*] blocks; the actual edit stays in the author's
hands (config files carry hand-written comments worth preserving)."""
from __future__ import annotations

from ..config import ConfigError
from ._common import add_instance_arg, fail, load


def add_parser(sub) -> None:
    p = sub.add_parser("migrate", help="config migration helpers")
    p.add_argument("what", choices=["config"])
    add_instance_arg(p)
    p.add_argument("--check", action="store_true", default=True,
                   help="report only (default; writing is left to the author)")
    p.set_defaults(func=run)


def run(args, extra) -> int:
    try:
        cfg = load(args)
    except ConfigError as e:
        return fail(str(e))
    if not cfg.deprecations:
        print("config: no deprecated keys — nothing to migrate")
        return 0
    print("Deprecated keys in paper.toml:")
    for d in cfg.deprecations:
        print(f"  - {d}")
    print("\nNormalized equivalent (copy into paper.toml, then delete the old keys):\n")

    def rel(p):
        try:
            return p.relative_to(cfg.root)
        except ValueError:
            return p

    if "paperforge" not in cfg.raw:
        print("[paperforge]\ninstance_schema = 1\n")
    for fm in cfg.formalizations:
        key = "primary" if fm.primary else fm.name
        print(f"[formalizations.{key}]")
        print(f'name = "{fm.name}"')
        print(f'root = "{rel(fm.root)}"')
        if fm.module:
            print(f'module = "{fm.module}"')
        if fm.docs_root:
            print(f'docs_root = "{fm.docs_root}"')
        print(f'declmap = "{rel(fm.declmap)}"')
        if fm.badge_cap is not None:
            print(f"badge_cap = {fm.badge_cap}")
        print()
    return 0

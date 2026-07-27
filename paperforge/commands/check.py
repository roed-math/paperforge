"""paperforge check: run the validator suite against the instance.

Delegates to the paperforge_validators package (kept as its own
pip-installable dist; `paperforge-check` remains a compatibility entry
point). When that dist is not installed, the copy in this checkout's
validators/ directory is used directly.
"""
from __future__ import annotations

import sys

from .. import tool_root
from ..config import ConfigError
from ._common import add_instance_arg, fail, resolve_instance


def add_parser(sub) -> None:
    p = sub.add_parser("check", help="run the deterministic validator suite")
    add_instance_arg(p)
    p.set_defaults(func=run)


def _import_run_all():
    try:
        from paperforge_validators import run_all
        return run_all
    except ImportError:
        sys.path.insert(0, str(tool_root() / "validators"))
        from paperforge_validators import run_all
        return run_all


def run(args, extra) -> int:
    try:
        root = resolve_instance(args)
    except ConfigError as e:
        return fail(str(e))
    run_all = _import_run_all()
    return run_all.main([str(root)])

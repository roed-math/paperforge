"""The `paperforge` command: deterministic onboarding, builds, and checks.

    paperforge init [PATH] [--title ... --slug ... --draft ... --no-lean ...]
    paperforge doctor [INSTANCE]
    paperforge status [INSTANCE]
    paperforge ingest [INSTANCE] [--bootstrap]
    paperforge accept lean-decl-map [INSTANCE] [--formalization NAME]
    paperforge build {web,arxiv,site} [INSTANCE] [--plan]
    paperforge check [INSTANCE] [validator args...]
    paperforge review [INSTANCE]
    paperforge migrate config [INSTANCE] [--check]

Every command takes the instance as an optional positional (default: the
nearest ancestor of the cwd containing paper.toml). Generative work is NOT
here — skills remain agent-executed; these commands stop at review
boundaries and print the next step (docs/ARCHITECTURE.md).
"""
from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="paperforge",
        description="deterministic commands for a paperforge paper instance")
    ap.add_argument("--version", action="version",
                    version=f"paperforge {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    from .commands import (accept, build, check, doctor, initcmd, ingest,
                           migrate, review, status)

    initcmd.add_parser(sub)
    doctor.add_parser(sub)
    status.add_parser(sub)
    ingest.add_parser(sub)
    accept.add_parser(sub)
    build.add_parser(sub)
    check.add_parser(sub)
    review.add_parser(sub)
    migrate.add_parser(sub)

    args, extra = ap.parse_known_args(argv)
    if extra and not getattr(args, "allows_extra", False):
        ap.error(f"unrecognized arguments: {' '.join(extra)}")
    try:
        return args.func(args, extra)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

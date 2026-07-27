"""Shared helpers for the subcommands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config import ConfigError, InstanceConfig, find_instance_root, load_instance


def add_instance_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("instance", nargs="?", default=None, metavar="INSTANCE",
                   help="instance root (default: nearest ancestor with paper.toml)")


def resolve_instance(args) -> Path:
    if args.instance:
        return Path(args.instance).resolve()
    root = find_instance_root(Path.cwd())
    if root is None:
        raise ConfigError(
            "no paper.toml here or above — run inside an instance, or pass "
            "its path (create one with `paperforge init`)")
    return root


def load(args) -> InstanceConfig:
    return load_instance(resolve_instance(args))


def fail(msg: str) -> int:
    print(f"paperforge: {msg}", file=sys.stderr)
    return 1

"""Build provenance: every build records what produced it; nothing blocks
a dirty development checkout (review §9 — schema compatibility is the hard
gate, exact pinning is opt-in and deliberately not implemented here yet).

The written file lives under the build output (not committed); the local
`source` path is for diagnostics and must be redacted/omitted by any
release-copy step.
"""
from __future__ import annotations

import datetime
import json
import platform
import subprocess
from pathlib import Path

from . import __version__, tool_root


def _git(repo: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True,
            stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def describe_repo(repo: Path) -> dict:
    commit = _git(repo, "rev-parse", "--short=12", "HEAD")
    dirty = None
    if commit is not None:
        status = _git(repo, "status", "--porcelain")
        dirty = bool(status)
    return {"commit": commit, "dirty": dirty}


def tool_description() -> dict:
    d = describe_repo(tool_root())
    d["version"] = __version__
    d["source"] = str(tool_root())
    return d


def pretext_version() -> str | None:
    try:
        return subprocess.check_output(
            ["pretext", "--version"], text=True,
            stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build_stamp(instance_root: Path, schema: int) -> dict:
    inst = describe_repo(instance_root)
    inst["schema"] = schema
    return {
        "paperforge": tool_description(),
        "instance": inst,
        "pretext": {"version": pretext_version()},
        "python": platform.python_version(),
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def write_provenance(out_dir: Path, instance_root: Path, schema: int) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "build-provenance.json"
    path.write_text(json.dumps(build_stamp(instance_root, schema), indent=2)
                    + "\n")
    return path


def short_stamp() -> str:
    """'abc1234+dirty' — for human-facing build banners."""
    d = describe_repo(tool_root())
    if d["commit"] is None:
        return __version__
    return d["commit"][:7] + ("+dirty" if d["dirty"] else "")

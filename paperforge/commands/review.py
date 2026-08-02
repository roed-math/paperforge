"""paperforge review: start the author review server for this instance.

One server per instance root, ever — a second writer once corrupted the
marks artifact mid-write. A PID file adds a friendly guard; the server's
own atomic writes remain the actual safety mechanism.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .. import tool_root
from ..config import ConfigError
from ._common import add_instance_arg, fail, load


def add_parser(sub) -> None:
    p = sub.add_parser("review", help="start the review dashboard/server")
    add_instance_arg(p)
    p.add_argument("--port", type=int, default=None,
                   help="port (default: the server's own default, 8765)")
    p.set_defaults(func=run)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


def run(args, extra) -> int:
    try:
        cfg = load(args)
    except ConfigError as e:
        return fail(str(e))
    web = cfg.web_output
    if not ((web / "paper.html").is_file() or (web / "index.html").is_file()):
        return fail(f"no web build at {web} — run `paperforge build web` first "
                    "(the review layer serves and annotates the built paper)")
    pid_file = cfg.root / ".cache" / "paperforge" / "review-server.pid"
    if pid_file.is_file():
        try:
            old = int(pid_file.read_text().strip())
        except ValueError:
            old = 0
        if old and _pid_alive(old):
            return fail(
                f"a review server for this instance appears to be running "
                f"(pid {old}, {pid_file}). One server per instance: a second "
                f"writer risks artifact corruption. Stop it first, or remove "
                f"the pid file if it is stale.")
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    server = tool_root() / "review" / "review_server.py"
    cmd = [sys.executable, str(server)]
    if args.port:
        cmd += ["--port", str(args.port)]
    print(f"starting review server (cwd {cfg.root}); Ctrl-C to stop")
    proc = subprocess.Popen(cmd, cwd=cfg.root)
    pid_file.write_text(str(proc.pid) + "\n")
    try:
        return proc.wait()
    finally:
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass

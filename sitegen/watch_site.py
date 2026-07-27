#!/usr/bin/env python3
"""Auto-rebuild the local site preview.

Watches the site source dir and mirrors any change into the assembled tree
on save, so a localhost preview reflects landing-page edits within ~1s.
This is a fast OVERLAY of the hand-authored layer only — it does NOT
rebuild the paper or Lean docs, and (having no --delete) it will not
propagate file *deletions*. For those, or a full clean assembly, run
build-site.sh.  Assumes build-site.sh has produced the assembled tree at
least once.

    python3 sitegen/watch_site.py [src] [dst]
    (defaults: web-assets/site -> output/site, relative to the cwd)
"""
import os
import subprocess
import sys
import time

SRC = os.path.join(sys.argv[1] if len(sys.argv) > 1 else
                   os.path.join("web-assets", "site"), "")
DST = os.path.join(sys.argv[2] if len(sys.argv) > 2 else
                   os.path.join("output", "site"), "")
POLL = 1.0        # seconds between mtime scans
DEBOUNCE = 0.8    # wait for writes to settle before syncing


def snapshot() -> float:
    """Newest mtime under SRC (0.0 if empty)."""
    sig = 0.0
    for dirpath, _dirs, files in os.walk(SRC):
        for fn in files:
            try:
                sig = max(sig, os.stat(os.path.join(dirpath, fn)).st_mtime)
            except FileNotFoundError:
                pass
    return sig


def sync() -> None:
    r = subprocess.run(
        ["rsync", "-a", "--exclude", ".DS_Store", "--exclude", "*~", SRC, DST],
        capture_output=True, text=True)
    ts = time.strftime("%H:%M:%S")
    if r.returncode == 0:
        print(f"[{ts}] synced {SRC} -> {DST}", flush=True)
    else:
        print(f"[{ts}] rsync FAILED rc={r.returncode}\n{r.stderr}", flush=True)


def main() -> None:
    if not os.path.isdir(DST):
        print(f"{DST} missing — run build-site.sh first", flush=True)
        return
    print(f"watch-site: mirroring {SRC} -> {DST} every {POLL}s "
          f"(Ctrl-C / TaskStop to stop)", flush=True)
    last = snapshot()
    while True:
        time.sleep(POLL)
        cur = snapshot()
        if cur <= last:
            continue
        while True:                       # debounce until writes settle
            time.sleep(DEBOUNCE)
            nxt = snapshot()
            if nxt == cur:
                break
            cur = nxt
        sync()
        last = cur


if __name__ == "__main__":
    main()

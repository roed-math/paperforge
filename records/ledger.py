#!/usr/bin/env python3
"""Build the deduplicated per-session token ledger for a cost page.

Reads the session ids listed in the records config (include-list only;
nothing else is ever opened), streams each main transcript plus its subagent
transcripts, and produces work/ledger.json under the pipeline home.

Counting rules (keep in sync with the instance's published token-accounting
definitions):

* Only lines with "type":"assistant" carry usage.  One API call (one
  message.id) can appear on several JSONL lines as it streams; each
  message.id is counted once, keeping the LAST occurrence's usage.
  Dedupe is global across the main transcript and all of the session's
  subagent transcripts, which also protects against older Claude Code
  versions that inline sidechain copies of subagent messages.
* Synthetic placeholder lines (model "<synthetic>" or missing usage) are
  skipped.
* processed tokens  = input + output + cache creation + cache read
* non-cache subtotal = input + output + cache creation   (excludes cache reads)

Usage:  python3 records/ledger.py [records-config.json]
"""
import glob
import json
import os
import sys
from collections import OrderedDict

from _config import load

USAGE_KEYS = ("input_tokens", "output_tokens",
              "cache_creation_input_tokens", "cache_read_input_tokens")

PUBLIC_MODEL_NAMES = {
    "claude-fable-5": "Fable 5",
    "claude-opus-4-8": "Opus 4.8",
    "claude-opus-4-7": "Opus 4.7",
    "claude-sonnet-4-5": "Sonnet 4.5",
    "claude-haiku-4-5": "Haiku 4.5",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
    "claude-haiku-5": "Haiku 5",
}


def public_model(model_id):
    if model_id in PUBLIC_MODEL_NAMES:
        return PUBLIC_MODEL_NAMES[model_id]
    return model_id


def iter_session_files(project_dir, session_id):
    """Main transcript plus subagent transcripts for one session."""
    main = os.path.join(project_dir, session_id + ".jsonl")
    if os.path.exists(main):
        yield main
    for sub in sorted(glob.glob(os.path.join(project_dir, session_id,
                                             "subagents", "agent-*.jsonl"))):
        yield sub


def scan_session(project_dir, session_id):
    """Stream one session (main + subagents); dedupe assistant usage by
    message.id with last occurrence winning."""
    by_id = OrderedDict()   # message.id -> (model, usage dict)
    anon = []               # assistant messages without an id (rare)
    first_ts = last_ts = None
    titles = []
    files = list(iter_session_files(project_dir, session_id))
    n_lines = 0
    for path in files:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                n_lines += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                ts = d.get("timestamp")
                if ts:
                    if first_ts is None or ts < first_ts:
                        first_ts = ts
                    if last_ts is None or ts > last_ts:
                        last_ts = ts
                dtype = d.get("type")
                if dtype in ("summary", "custom-title", "ai-title"):
                    text = (d.get("summary") or d.get("aiTitle")
                            or d.get("customTitle"))
                    if text:
                        titles.append((dtype, text))
                if dtype != "assistant":
                    continue
                msg = d.get("message") or {}
                model = msg.get("model")
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                if model == "<synthetic>" or model is None:
                    continue
                u = {k: usage.get(k) or 0 for k in USAGE_KEYS}
                mid = msg.get("id")
                if mid:
                    by_id[mid] = (model, u)   # last occurrence wins
                else:
                    anon.append((model, u))

    per_model = {}
    for model, u in list(by_id.values()) + anon:
        acc = per_model.setdefault(model, {k: 0 for k in USAGE_KEYS})
        acc.setdefault("calls", 0)
        for k in USAGE_KEYS:
            acc[k] += u[k]
        acc["calls"] += 1

    totals = {k: sum(m[k] for m in per_model.values()) for k in USAGE_KEYS}
    processed = sum(totals.values())
    non_cache = processed - totals["cache_read_input_tokens"]

    title = None
    for kind in ("ai-title", "summary", "custom-title"):
        for tk, tv in reversed(titles):
            if tk == kind:
                title = tv
                break
        if title:
            break

    return {
        "session": session_id,
        "files": len(files),
        "lines": n_lines,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "title": title,
        "models": sorted(public_model(m) for m in per_model),
        "per_model": {public_model(m): v for m, v in sorted(per_model.items())},
        "usage": totals,
        "calls": sum(m["calls"] for m in per_model.values()),
        "processed_tokens": processed,
        "non_cache_tokens": non_cache,
    }


def main():
    rc = load(sys.argv[1:])
    project_dirs = rc.project_dirs
    out_path = os.path.join(rc.work, "ledger.json")

    def locate(prefix):
        for pd in project_dirs:
            hits = sorted(glob.glob(os.path.join(pd, prefix + "*.jsonl")))
            hits = [h for h in hits if os.path.basename(h) != "memory"]
            if hits:
                sid = os.path.basename(hits[0])[:-6]
                return pd, sid
        raise SystemExit("session prefix not found: " + prefix)

    ledger = {"categories": {}, "generated_note":
              "Deduplicated by message.id (last occurrence wins), subagent "
              "transcripts included, synthetic placeholders excluded."}
    import datetime
    ledger["generated_utc"] = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for cat, spec in rc["categories"].items():
        rows = []
        for prefix in spec["sessions"]:
            pd, sid = locate(prefix)
            sys.stderr.write("scanning %s/%s\n" % (cat, prefix))
            sys.stderr.flush()
            row = scan_session(pd, sid)
            row["prefix"] = prefix
            rows.append(row)
        agg_models = {}
        for row in rows:
            for m, v in row["per_model"].items():
                acc = agg_models.setdefault(
                    m, {k: 0 for k in USAGE_KEYS} | {"calls": 0})
                for k in USAGE_KEYS:
                    acc[k] += v[k]
                acc["calls"] += v["calls"]
        totals = {k: sum(r["usage"][k] for r in rows) for k in USAGE_KEYS}
        processed = sum(totals.values())
        ledger["categories"][cat] = {
            "label": spec["label"],
            "sessions": rows,
            "session_count": len(rows),
            "per_model": agg_models,
            "usage": totals,
            "processed_tokens": processed,
            "non_cache_tokens": processed - totals["cache_read_input_tokens"],
            "first_ts": min(r["first_ts"] for r in rows if r["first_ts"]),
            "last_ts": max(r["last_ts"] for r in rows if r["last_ts"]),
        }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(ledger, fh, indent=1, sort_keys=True)
    for cat, c in ledger["categories"].items():
        print("%-20s  sessions=%2d  processed=%14d  non_cache=%12d  calls=%d"
              % (cat, c["session_count"], c["processed_tokens"],
                 c["non_cache_tokens"],
                 sum(m["calls"] for m in c["per_model"].values())))
    print("wrote", out_path)


if __name__ == "__main__":
    main()

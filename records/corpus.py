#!/usr/bin/env python3
"""Build a sanitized session corpus: per-session message payloads, a
deterministic archive, and an audit report.

Reads the records config ("cleanup_corpus" block + "session_order" +
exclusions.json beside the config), extracts published messages with
sanitize.extract_messages + sanitize.redact, applies the editorial
exclusions, audits the result, and writes under work/cleanup/:

  <category>__session_NN.msgs.json     sanitized message arrays
  archive/<archive_name>/{prefix}.jsonl
  <archive_name>.tar.gz                (deterministic)
  audit-report.txt                     human review findings
  summary.json                         counts, models, hashes

Raw transcripts are never copied anywhere; only sanitized assistant text
leaves the local project directory.  Everything here is re-runnable; adding
a new session id to the config appends a new NN without renumbering.

Config block:

    "cleanup_corpus": {
      "category": "roe_cleanup",             # sessions + exclusions key
      "archive_name": "gq2-lean-cleanup-session-logs",
      "manifest_header": ["line", ...]       # "{count}" -> session count
    }

Usage:  python3 records/corpus.py [records-config.json]
"""
import glob
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile

from _config import load
from sanitize import extract_messages, redact, audit_text, configure


def locate(project_dirs, prefix):
    for pd in project_dirs:
        hits = sorted(glob.glob(os.path.join(pd, prefix + "*.jsonl")))
        if hits:
            return hits[0]
    raise SystemExit("session prefix not found: " + prefix)


def all_local_session_ids(project_dirs):
    ids = []
    for pd in project_dirs:
        for f in glob.glob(os.path.join(pd, "*.jsonl")):
            ids.append(os.path.basename(f)[:-6])
    return ids


def user_fragments(path, min_len=15):
    """Verbatim human-prompt fragments used to detect user echoes in
    assistant text.  The fragments themselves never leave this process."""
    frags = set()
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "user" or d.get("isMeta"):
            continue
        msg = d.get("message") or {}
        c = msg.get("content")
        texts = []
        if isinstance(c, str):
            texts = [c]
        elif isinstance(c, list):
            texts = [p.get("text", "") for p in c
                     if isinstance(p, dict) and p.get("type") == "text"]
        for t in texts:
            t = t.strip()
            if t.startswith("<") or "tool_result" in t[:40]:
                continue
            for linefrag in t.splitlines():
                linefrag = linefrag.strip()
                if len(linefrag) >= min_len and not linefrag.startswith("["):
                    frags.add(linefrag)
    return frags


def session_title(path):
    title = {}
    for line in open(path, errors="replace"):
        if '"ai-title"' not in line and '"summary"' not in line \
                and '"custom-title"' not in line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = d.get("type")
        if t == "ai-title" and d.get("aiTitle"):
            title["ai"] = d["aiTitle"]
        elif t == "summary" and d.get("summary"):
            title["summary"] = d["summary"]
        elif t == "custom-title" and d.get("customTitle"):
            title["custom"] = d["customTitle"]
    return title.get("ai") or title.get("summary") or title.get("custom")


def main():
    rc = load(sys.argv[1:])
    configure(rc.get("sanitize"))
    corpus_cfg = rc["cleanup_corpus"]
    category = corpus_cfg["category"]
    archive_name = corpus_cfg["archive_name"]
    work = os.path.join(rc.work, "cleanup")

    project_dirs = rc.project_dirs
    order = rc["session_order"][category]
    exclusions = {}
    if os.path.exists(rc.exclusions_path):
        with open(rc.exclusions_path) as fh:
            exclusions = json.load(fh).get(category, {})

    ids = all_local_session_ids(project_dirs)
    redact_ids = ids + [s[:8] for s in ids]

    os.makedirs(work, exist_ok=True)
    member_dir = os.path.join(work, "archive", archive_name)
    os.makedirs(member_dir, exist_ok=True)

    audit_lines = []
    summary = {"sessions": []}
    manifest_rows = []

    for nn, prefix in enumerate(order, 1):
        path = locate(project_dirs, prefix)
        msgs = extract_messages(path)
        raw_count = len(msgs)
        excl = exclusions.get(prefix, [])
        excl_ts = {e["timestamp"] for e in excl}
        kept = []
        for m in msgs:
            if m["timestamp"] in excl_ts and any(
                    e["timestamp"] == m["timestamp"] and
                    m["text"].startswith(e.get("text_prefix", ""))
                    for e in excl):
                continue
            kept.append(dict(m, text=redact(m["text"], redact_ids)))
        title = redact(session_title(path) or "(untitled)", redact_ids)

        frags = user_fragments(path)
        echo_hits = []
        for i, m in enumerate(kept):
            for f in frags:
                if f in m["text"]:
                    echo_hits.append((i, f[:60]))
            for label, excerpt in audit_text(m["text"]):
                audit_lines.append("session %02d msg %d [%s]: %r" %
                                  (nn, i, label, excerpt))
        for i, f in echo_hits:
            audit_lines.append("session %02d msg %d [user echo]: %r" %
                              (nn, i, f))

        key = "%s__session_%02d" % (category, nn)
        payload_path = os.path.join(work, key + ".msgs.json")
        with open(payload_path, "w") as fh:
            json.dump(msgs and kept, fh, ensure_ascii=False, indent=1)

        # archive member: one JSON object per line, published-record schema
        member_path = os.path.join(member_dir, prefix + ".jsonl")
        with open(member_path, "w") as fh:
            for m in kept:
                fh.write(json.dumps(m, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        member_sha = hashlib.sha256(open(member_path, "rb").read()).hexdigest()

        models = sorted({m["model"] for m in kept})
        summary["sessions"].append({
            "nn": nn, "prefix": prefix,
            "session_id": os.path.basename(path)[:-6],
            "title": title,
            "messages": len(kept),
            "raw_messages": raw_count,
            "excluded": raw_count - len(kept),
            "models": models,
            "first_timestamp": kept[0]["timestamp"] if kept else None,
            "last_timestamp": kept[-1]["timestamp"] if kept else None,
            "member_sha256": member_sha,
        })
        manifest_rows.append((kept[0]["timestamp"][:10] if kept else "?",
                              prefix, len(kept), title))

    # MANIFEST.txt: instance-authored header lines + the session table
    lines = [line.replace("{count}", str(len(summary["sessions"])))
             for line in corpus_cfg["manifest_header"]]
    for date, prefix, n, title in manifest_rows:
        lines.append("%s  %s  %8d  %s" % (date, prefix, n, title[:60]))
    manifest_text = "\n".join(lines) + "\n"
    with open(os.path.join(member_dir, "MANIFEST.txt"), "w") as fh:
        fh.write(manifest_text)

    # deterministic tar.gz: sorted members, fixed metadata, gzip mtime 0
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
        members = [archive_name] + sorted(
            os.path.join(archive_name, f) for f in os.listdir(member_dir))
        for rel in members:
            full = os.path.join(work, "archive", rel)
            info = tarfile.TarInfo(rel)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if os.path.isdir(full):
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            else:
                data = open(full, "rb").read()
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
    gz_path = os.path.join(work, archive_name + ".tar.gz")
    with open(gz_path, "wb") as fh:
        gz = gzip.GzipFile(fileobj=fh, mode="wb", mtime=0)
        gz.write(tar_bytes.getvalue())
        gz.close()

    summary["archive"] = {
        "file": gz_path,
        "bytes": os.path.getsize(gz_path),
        "sha256": hashlib.sha256(open(gz_path, "rb").read()).hexdigest(),
    }
    summary["published_messages"] = sum(s["messages"] for s in summary["sessions"])
    with open(os.path.join(work, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    with open(os.path.join(work, "audit-report.txt"), "w") as fh:
        fh.write("\n".join(audit_lines) + ("\n" if audit_lines else ""))

    for s in summary["sessions"]:
        print("%02d %s msgs=%4d (excl %d) models=%s  %s" % (
            s["nn"], s["prefix"], s["messages"], s["excluded"],
            ",".join(s["models"]), s["title"]))
    print("archive: %s (%d bytes)" % (gz_path, summary["archive"]["bytes"]))
    print("audit findings: %d  -> %s" % (
        len(audit_lines), os.path.join(work, "audit-report.txt")))


if __name__ == "__main__":
    main()

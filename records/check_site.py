#!/usr/bin/env python3
"""Post-application sanity checks for the development dashboard + cost page.

Run after apply_site.py.  Exits nonzero on any failure.

Checks:
 1. data.js parses and round-trips byte-exactly under the canonical serializer.
 2. Every node has stage/lane defined; stage_order/lane_order cover them.
 3. census/dataset public_records == node count; counts == class histogram;
    message_roles.assistant == corpus messages + scaffold baseline.
 4. Every corpus node has a content file and vice versa; content files
    contain assistant-only messages (no user/tool text), no absolute local
    paths, no raw home directories, no known secret shapes.
 5. corpora/manifest.json outputs cover the corpus content files with correct
    sha256 and message counts; pinned hashes (config "pinned_inputs" and old
    outputs) unchanged; archive shas match the manifest.
 6. cost/session-ledger.json parses; session numbering for the formalization
    category matches the published record keys; cost/index.html has no
    unfilled ledger spans.
 7. every configured download archive covers its records byte-exactly and
    the index links each archive (config "required_index_links").

Identity comes from the same config blocks the builders use; check-specific
knobs live under "check_site".  Usage:

    python3 records/check_site.py [records-config.json]
"""
import glob
import hashlib
import json
import os
import re
import sys
import tarfile

from _config import load
from sanitize import BASE_KEEP_EMAILS

failures = []


def check(cond, msg):
    if cond:
        print("ok:", msg)
    else:
        failures.append(msg)
        print("FAIL:", msg)


def main():
    rc = load(sys.argv[1:])
    cfg = rc["check_site"]
    apply_cfg = rc["apply_site"]
    site = rc.site_dev
    data_global = apply_cfg.get("data_global", "Q2DATA")
    category = rc["cleanup_corpus"]["category"]
    stage_id = apply_cfg["stage_id"]
    archive_name = rc["cleanup_corpus"]["archive_name"]

    # 1. data.js round-trip
    text = open(os.path.join(site, "data.js")).read()
    m = re.match(r"^window\.%s\s*=\s*(.*?);?\s*\Z" % data_global, text, re.S)
    check(m is not None, "data.js has the window.%s wrapper" % data_global)
    data = json.loads(m.group(1))
    rt = ("window.%s = " % data_global + json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + ";\n")
    check(rt == text, "data.js round-trips under the canonical serializer")

    # 2. structure
    nodes = data["nodes"]
    check(all(n.get("stage_id") in data["stages"] for n in nodes),
          "every node's stage_id is defined in stages")
    check(all(n.get("lane") in data["lanes"] for n in nodes),
          "every node's lane is defined in lanes")
    check(set(data["stage_order"]) == set(data["stages"]),
          "stage_order covers exactly the stages")
    check(set(data["lane_order"]) == set(data["lanes"]),
          "lane_order covers exactly the lanes")

    # 3. counts
    check(data["census"]["public_records"] == len(nodes),
          "census.public_records == node count (%d)" % len(nodes))
    check(data["dataset"]["public_records"] == len(nodes),
          "dataset.public_records == node count")
    hist = {}
    for n in nodes:
        hist[n["class"]] = hist.get(n["class"], 0) + 1
    check(data["counts"] == hist, "counts equals the class histogram")
    check(data["tmax"] == max(n["datetime"] for n in nodes if n.get("datetime")),
          "tmax equals the max node datetime")

    corpus_nodes = [n for n in nodes if n["stage_id"] == stage_id]
    check(data["census"].get("cleanup_corpus_records") == len(corpus_nodes),
          "census.cleanup_corpus_records == corpus node count (%d)"
          % len(corpus_nodes))

    # 4. corpus node <-> content coverage and content hygiene
    content_files = sorted(glob.glob(
        os.path.join(site, "content", category + "__session_*.json")))
    check({n["key"] for n in corpus_nodes}
          == {os.path.basename(p)[:-5] for p in content_files},
          "corpus nodes and content files match one-to-one")
    total_msgs = 0
    bad = []
    secret_re = re.compile(
        r"sk-ant-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"
        r"|-----BEGIN [A-Z ]*PRIVATE KEY-----")
    email_re = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    keep_emails = BASE_KEEP_EMAILS | set(
        rc.get("sanitize", {}).get("keep_emails", []))
    for p in content_files:
        obj = json.load(open(p))
        for i, msg in enumerate(obj["msgs"]):
            total_msgs += 1
            if msg["role"] != "assistant":
                bad.append("%s msg %d role %s" % (p, i, msg["role"]))
            t = msg["text"]
            if "/Users/" in t or "/home/" in t or "~/" in t:
                bad.append("%s msg %d has a local path" % (p, i))
            if secret_re.search(t):
                bad.append("%s msg %d matches a secret pattern" % (p, i))
            for em in email_re.findall(t):
                if em not in keep_emails and em != "[redacted-email]":
                    bad.append("%s msg %d has email %s" % (p, i, em))
    check(not bad, "corpus content files are assistant-only and sanitized"
          + ("" if not bad else " (%s...)" % bad[0]))

    # assistant message-role total: baseline (non-corpus) + corpus msgs
    baseline = rc["published_baseline"]["assistant_msgs"]
    check(data["census"]["message_roles"]["assistant"] == baseline + total_msgs,
          "census assistant messages == %d + %d corpus" % (baseline, total_msgs))

    # 5. manifest
    manifest = json.load(open(os.path.join(site, "corpora", "manifest.json")))
    outs = {o["key"]: o for o in manifest["outputs"]}
    for p in content_files:
        key = os.path.basename(p)[:-5]
        sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
        o = outs.get(key)
        check(o is not None and o["sha256"] == sha
              and o["messages"] == len(json.load(open(p))["msgs"]),
              "manifest output %s matches file hash and count" % key)
    # pinned old outputs still match their files (keys with no site file are
    # skipped: some archives key days rather than per-record content files)
    for key, o in outs.items():
        if key.startswith(category + "__"):
            continue
        path = os.path.join(site, "content", key + ".json")
        if not os.path.exists(path):
            continue
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        check(o["sha256"] == sha, "pinned manifest hash unchanged for %s" % key)
    for key, val in cfg.get("pinned_inputs", {}).items():
        check(manifest["inputs"].get(key) == val,
              "pinned %s untouched" % key)
    arch = os.path.join(site, "corpora", archive_name + ".tar.gz")
    sha = hashlib.sha256(open(arch, "rb").read()).hexdigest()
    check(manifest["inputs"][apply_cfg["manifest_archive_sha_key"]] == sha,
          "corpus archive sha256 matches manifest")

    # 6. session ledger + cost page
    ledger = json.load(open(os.path.join(site, "cost", "session-ledger.json")))
    form_cat = cfg["formalization_category"]
    form_rows = [r for r in ledger["sessions"] if r["category"] == form_cat]
    check(len(form_rows) == cfg["formalization_rows"],
          "session ledger has %d formalization rows" % cfg["formalization_rows"])
    # numbering must be consistent with published records: node NN's datetime
    # (first assistant message) must fall inside ledger row NN's session span.
    node_dt = {n["key"]: n["datetime"] for n in nodes}
    mismatched = []
    for i, r in enumerate(form_rows, 1):
        key = "%s__session_%02d" % (form_cat, i)
        dt = node_dt.get(key, "")[:19]
        lo = (r["first_timestamp"] or "")[:19]
        hi = (r["last_timestamp"] or "9999")[:19]
        if not (lo <= dt <= hi):
            mismatched.append((i, dt, lo, hi))
    check(not mismatched,
          "formalization ledger numbering consistent with published records %s"
          % (mismatched[:2] if mismatched else ""))
    cost_html = open(os.path.join(site, "cost", "index.html")).read()
    check("&bull;</span>" not in cost_html and ">•<" not in cost_html,
          "cost page has no unfilled ledger spans")

    corpus_rows = [r for r in ledger["sessions"] if r["category"] == category]
    check(len(corpus_rows) == len(corpus_nodes),
          "session ledger corpus rows match corpus node count")

    # 7. transcript downloads cover every record; index header is consistent
    ra_cfg = rc.get("research_archives", {})
    corpus_stages = set(ra_cfg.get("corpus_stages", []))
    for b in ra_cfg.get("bundles", []):
        if b.get("stage"):
            keys = sorted(n["key"] for n in nodes
                          if n["stage_id"] == b["stage"])
        else:
            keys = sorted(n["key"] for n in nodes
                          if n["stage_id"] not in corpus_stages)
        arch = os.path.join(site, "corpora", b["name"] + ".tar.gz")
        check(os.path.exists(arch), "%s archive exists" % b["name"])
        if not os.path.exists(arch):
            continue
        sha = hashlib.sha256(open(arch, "rb").read()).hexdigest()
        check(sha == manifest["inputs"].get(b["sha_key"]),
              "%s archive sha256 matches manifest" % b["name"])
        if b.get("sources_key"):
            check(manifest["inputs"].get(b["sources_key"], {}).get("records")
                  == len(keys),
                  "manifest %s record count == selected node count (%d)"
                  % (b["sources_key"], len(keys)))
        stale = []
        with tarfile.open(arch) as tar:
            names = sorted(m.name for m in tar.getmembers() if m.isfile())
            for mm in tar.getmembers():
                if not mm.isfile():
                    continue
                site_path = os.path.join(site, "content",
                                         os.path.basename(mm.name))
                if (hashlib.sha256(tar.extractfile(mm).read()).hexdigest()
                        != hashlib.sha256(open(site_path, "rb").read()).hexdigest()):
                    stale.append(os.path.basename(mm.name))
        check(names == ["%s/%s.json" % (b["name"], k) for k in keys]
              and not stale,
              "%s members byte-match the site content files" % b["name"]
              + ("" if not stale else " (stale: %s)" % stale[:2]))

    idx = open(os.path.join(site, "index.html")).read()
    for href in cfg.get("required_index_links", []):
        check(href in idx, "index links the archive %s" % href.split("/")[-1])
    span = re.search(r'<span data-census="public_records">([\d,]+)</span>', idx)
    check(span is not None and
          int(span.group(1).replace(",", "")) == data["census"]["public_records"],
          "index record-count span matches census")
    if cfg.get("check_accounting_note"):
        note = re.search(r'<details class="accounting-note".*?</details>', idx, re.S)
        check(note is not None and "processed tokens" not in note.group(0),
              "transcript-files note carries no token figures")

    print()
    if failures:
        print("%d CHECK(S) FAILED" % len(failures))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()

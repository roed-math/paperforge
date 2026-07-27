#!/usr/bin/env python3
"""Apply the corpus and cost-ledger outputs to the development-dashboard tree.

Idempotent: every run rebuilds the corpus-derived portions of

  <site_dev>/content/<category>__session_NN.json
  <site_dev>/corpora/<archive_name>.tar.gz
  <site_dev>/corpora/manifest.json      (corpus keys only)
  <site_dev>/data.js                    (corpus stage/lane/nodes + counts)
  <site_dev>/index.html                 (data-census record-count spans)
  <site_dev>/cost/session-ledger.json / .csv
  <site_dev>/cost/index.html            (data-ledger number spans)

from the pipeline's work/ (ledger.json + cleanup/summary.json + payloads).
Pinned history (existing manifest hashes, non-corpus records) is never
modified.  Run ledger.py and corpus.py first; run_all.py does the whole
sequence.

All dashboard identity and prose comes from the records config's
"apply_site" block — the data.js global, stage/lane/attribution objects,
node templates, ledger category labels and name prefixes — so this file
carries mechanics only.  See gq2-paper's records-pipeline/config.json for
the worked example.

Usage:  python3 records/apply_site.py [records-config.json]
"""
import csv
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys

from _config import load
from sanitize import redact, configure

USAGE_KEYS = ("input_tokens", "output_tokens",
              "cache_creation_input_tokens", "cache_read_input_tokens")

# Claude list prices, $/MTok (input, output); cache write bills 1.25x input,
# cache read 0.1x input.  Used only for the "API-equivalent" sentences;
# override with an "apply_site"."claude_rates" mapping if these age out.
CLAUDE_RATES = {
    "Fable 5": (10, 50),
    "Opus 4.8": (5, 25),
    "Opus 4.7": (5, 25),
    "Haiku 4.5": (1, 5),
    "claude-haiku-4-5-20251001": (1, 5),
}


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Site:
    """Paths + config for one apply run."""

    def __init__(self, rc):
        self.rc = rc
        self.cfg = rc["apply_site"]
        self.site = rc.site_dev
        self.work = rc.work
        self.clean = os.path.join(rc.work, "cleanup")
        self.category = rc["cleanup_corpus"]["category"]
        self.archive_name = rc["cleanup_corpus"]["archive_name"]
        self.stage_id = self.cfg["stage_id"]
        self.lane_id = self.cfg["lane_id"]
        self.data_global = self.cfg.get("data_global", "Q2DATA")
        self.rates = self.cfg.get("claude_rates", CLAUDE_RATES)

    def key(self, nn):
        return "%s__session_%02d" % (self.category, nn)

    def read_data(self):
        path = os.path.join(self.site, "data.js")
        text = open(path).read()
        m = re.match(r"^window\.%s\s*=\s*(.*?);?\s*\Z" % self.data_global,
                     text, re.S)
        return path, json.loads(m.group(1))


# ---------------------------------------------------------------------------
# content files
# ---------------------------------------------------------------------------

def write_content(st, summary):
    keys = []
    for s in summary["sessions"]:
        key = st.key(s["nn"])
        msgs = load_json(os.path.join(st.clean, key + ".msgs.json"))
        detail = dict(st.cfg["record_source_detail"])
        detail["artifact_sha256"] = s["member_sha256"]
        detail["artifact_sha256_of"] = (
            st.cfg["artifact_sha256_of_template"]
            .format(prefix=s["prefix"], archive=st.archive_name))
        obj = {
            "key": key,
            "msgs": msgs,
            "source": st.cfg["record_source"],
            "source_detail": detail,
        }
        path = os.path.join(st.site, "content", key + ".json")
        with open(path, "w") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True)
            fh.write("\n")
        keys.append((key, s, path))
    # remove stale corpus content files beyond the current count
    for path in glob.glob(os.path.join(st.site, "content",
                                       st.category + "__session_*.json")):
        nn = int(re.search(r"_(\d+)\.json$", path).group(1))
        if nn > len(summary["sessions"]):
            os.remove(path)
    return keys


# ---------------------------------------------------------------------------
# data.js
# ---------------------------------------------------------------------------

def make_node(st, s):
    models = s["models"]
    model_text = ", ".join(models)
    tag = ("Model: " if len(models) == 1 else "Models: ") + model_text
    ts = s["first_timestamp"]
    node_cfg = st.cfg["node"]
    return {
        "class": node_cfg.get("class", "artifact"),
        "datetime": ts,
        "key": st.key(s["nn"]),
        "lane": st.lane_id,
        "link": None,
        "model_public_text": model_text,
        "source": st.cfg["record_source"],
        "source_detail": dict(st.cfg["record_source_detail"]),
        "stage_id": st.stage_id,
        "summary": node_cfg["summary_template"].format(title=s["title"]),
        "tag": tag,
        "thinking_seconds": None,
        "timestamp": {
            "ordering": "datetime",
            "precision": "second",
            "raw_value": ts,
            "source": node_cfg["timestamp_source"],
            "timezone": "UTC",
            "timezone_interpretation": node_cfg["timezone_interpretation"],
            "value": ts,
        },
        "turn": s["nn"],
        "why": node_cfg["why"],
    }


def patch_data_js(st, summary):
    path, data = st.read_data()

    data["nodes"] = [n for n in data["nodes"] if n.get("stage_id") != st.stage_id]

    new_nodes = [make_node(st, s) for s in summary["sessions"]]
    new_msgs = sum(s["messages"] for s in summary["sessions"])
    data["nodes"].extend(new_nodes)

    # stage
    max_order = max(stg.get("order", 0) for sid, stg in data["stages"].items()
                    if sid != st.stage_id)
    first_day = min(s["first_timestamp"] for s in summary["sessions"])[:10]
    last_day = max(s["last_timestamp"] for s in summary["sessions"])[:10]
    date_label = st.cfg["date_label_template"].format(
        first=int(first_day[8:10]), last=int(last_day[8:10]))
    stage = dict(st.cfg["stage"])
    stage["date_label"] = date_label
    stage["id"] = st.stage_id
    stage["order"] = data["stages"].get(st.stage_id, {}).get("order", max_order + 1)
    data["stages"][st.stage_id] = stage
    if st.stage_id not in data["stage_order"]:
        data["stage_order"].append(st.stage_id)

    # lane
    max_lane_order = max(l.get("order", 0) for lid, l in data["lanes"].items()
                         if lid != st.lane_id)
    lane = dict(st.cfg["lane"])
    lane["order"] = data["lanes"].get(st.lane_id, {}).get("order", max_lane_order + 1)
    data["lanes"][st.lane_id] = lane
    if st.lane_id not in data["lane_order"]:
        data["lane_order"].append(st.lane_id)

    # model attribution rule
    rule = dict(st.cfg["attribution_rule"])
    rule["selector"] = {"lanes": [st.lane_id]}
    rules = [r for r in data["model_attribution"]["rules"]
             if r.get("id") != rule["id"]]
    rules.append(rule)
    data["model_attribution"]["rules"] = rules

    # census / dataset / counts. The assistant total is recomputed from the
    # frozen pre-corpus baseline rather than by delta, so re-runs after the
    # corpus sessions have grown stay correct (content files are rewritten
    # before this function runs, so no "old" count survives on disk).
    baseline = st.rc["published_baseline"]["assistant_msgs"]
    for block_name in ("census", "dataset"):
        block = data[block_name]
        block["public_records"] = len(data["nodes"])
        block["cleanup_corpus_records"] = len(new_nodes)
        block["message_roles"]["assistant"] = baseline + new_msgs
    counts = {}
    for node in data["nodes"]:
        counts[node["class"]] = counts.get(node["class"], 0) + 1
    data["counts"] = counts
    data["tmax"] = max(n["datetime"] for n in data["nodes"] if n.get("datetime"))

    out = ("window.%s = " % st.data_global +
           json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")) + ";\n")
    with open(path, "w") as fh:
        fh.write(out)
    return data


# ---------------------------------------------------------------------------
# corpora/manifest.json + archive copy
# ---------------------------------------------------------------------------

def patch_manifest(st, summary, content_keys, data):
    src = os.path.join(st.clean, st.archive_name + ".tar.gz")
    dst = os.path.join(st.site, "corpora", st.archive_name + ".tar.gz")
    shutil.copyfile(src, dst)

    path = os.path.join(st.site, "corpora", "manifest.json")
    manifest = load_json(path)

    member_shas = sorted(s["member_sha256"] for s in summary["sessions"])
    manifest["inputs"][st.cfg["manifest_sources_key"]] = {
        "first_timestamp": min(s["first_timestamp"] for s in summary["sessions"]),
        "last_timestamp": max(s["last_timestamp"] for s in summary["sessions"]),
        "published_messages": summary["published_messages"],
        "source_file_count": len(summary["sessions"]),
        "sanitized_member_set_sha256": hashlib.sha256(
            "\n".join(member_shas).encode()).hexdigest(),
        "sanitized_member_set_sha256_definition":
            "sha256 of the newline-joined sorted sha256 hashes of the "
            "sanitized archive members (assistant-only extraction; raw "
            "transcripts stay private).",
    }
    manifest["inputs"][st.cfg["manifest_archive_sha_key"]] = summary["archive"]["sha256"]

    outputs = [o for o in manifest["outputs"]
               if not o["key"].startswith(st.category + "__")]
    for key, s, cpath in content_keys:
        outputs.append({
            "key": key,
            "messages": s["messages"],
            "models": s["models"],
            "sha256": hashlib.sha256(open(cpath, "rb").read()).hexdigest(),
        })
    manifest["outputs"] = outputs

    manifest["counts"]["cleanup_generated_records"] = len(summary["sessions"])
    manifest["counts"][st.cfg["manifest_messages_count_key"]] = summary["published_messages"]
    manifest["counts"]["final_public_records"] = data["census"]["public_records"]
    manifest["cleanup_generated_utc"] = now_utc()
    manifest["policy"]["cleanup_included"] = st.cfg["manifest_policy_note"]

    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------------------
# index.html record-count spans
# ---------------------------------------------------------------------------

def patch_index(st):
    """Refresh <span data-census="..."> spans in the development index.

    Each such span names a key of data.js's census block and is refreshed
    from it here (header token figures, when any, live on the cost page)."""
    path = os.path.join(st.site, "index.html")
    html = open(path).read()
    _, data = st.read_data()
    census = data["census"]

    def fill(m):
        key = m.group(1)
        if key not in census:
            raise SystemExit(
                "index.html data-census key %r not in data.js census" % key)
        return '<span data-census="%s">%s</span>' % (
            key, format(census[key], ","))

    html = re.sub(r'<span data-census="([^"]+)">[^<]*</span>', fill, html)
    with open(path, "w") as fh:
        fh.write(html)


# ---------------------------------------------------------------------------
# cost/session-ledger.json + .csv + number refresh in cost/index.html
# ---------------------------------------------------------------------------

def build_session_ledger(st, ledger):
    os.makedirs(os.path.join(st.site, "cost"), exist_ok=True)
    # every local session id (full and prefix) is a redaction target in
    # published titles, except those an archive already exposes
    all_ids = []
    for pd in st.rc.project_dirs:
        for f in glob.glob(os.path.join(pd, "*.jsonl")):
            all_ids.append(os.path.basename(f)[:-6])
    redact_ids = all_ids + [s[:8] for s in all_ids]
    archived = set(st.cfg["archived_categories"])
    name_prefix = st.cfg["session_name_prefixes"]
    rows = []
    for cat in st.cfg["ledger_categories"]:
        c = ledger["categories"][cat]
        for i, s in enumerate(c["sessions"], 1):
            row = {
                "category": cat,
                "session": "%s-%02d" % (name_prefix[cat], i),
                "session_id": s["prefix"] if cat in archived else None,
                "title": redact(s["title"] or "(untitled)", redact_ids),
                "first_timestamp": s["first_ts"],
                "last_timestamp": s["last_ts"],
                "models": s["models"],
                "api_calls": s["calls"],
                "input_tokens": s["usage"]["input_tokens"],
                "output_tokens": s["usage"]["output_tokens"],
                "cache_creation_tokens": s["usage"]["cache_creation_input_tokens"],
                "cache_read_tokens": s["usage"]["cache_read_input_tokens"],
                "processed_tokens": s["processed_tokens"],
                "non_cache_tokens": s["non_cache_tokens"],
            }
            rows.append(row)
    obj = {
        "definitions": {
            "processed_tokens": "input + output + cache creation + cache read, "
                                "matching methods/token-accounting.json.",
            "non_cache_tokens": "input + output + cache creation; excludes "
                                "cache reads.",
            "method": "Deduplicated by API message id (last occurrence wins) "
                      "across each session's main transcript and all of its "
                      "subagent transcripts; synthetic placeholder lines "
                      "excluded.",
            "session_id": "Present only for sessions whose id an existing "
                          "public archive already exposes.",
            "snapshot": "Website/PaperForge sessions and the newest cleanup "
                        "sessions were still active when measured; totals are "
                        "a snapshot at generated_utc.",
        },
        "generated_utc": ledger["generated_utc"],
        "category_labels": st.cfg["category_labels"],
        "sessions": rows,
        "category_totals": {
            cat: {
                "sessions": ledger["categories"][cat]["session_count"],
                "processed_tokens": ledger["categories"][cat]["processed_tokens"],
                "non_cache_tokens": ledger["categories"][cat]["non_cache_tokens"],
                "per_model": ledger["categories"][cat]["per_model"],
                "first_timestamp": ledger["categories"][cat]["first_ts"],
                "last_timestamp": ledger["categories"][cat]["last_ts"],
            } for cat in ledger["categories"]
        },
    }
    with open(os.path.join(st.site, "cost", "session-ledger.json"), "w") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    cols = ["category", "session", "session_id", "title", "first_timestamp",
            "last_timestamp", "models", "api_calls", "input_tokens",
            "output_tokens", "cache_creation_tokens", "cache_read_tokens",
            "processed_tokens", "non_cache_tokens"]
    with open(os.path.join(st.site, "cost", "session-ledger.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            r = dict(r, models="; ".join(r["models"]),
                     session_id=r["session_id"] or "")
            w.writerow([r[c] for c in cols])
    return obj


def comma(n):
    return "{:,}".format(n)


def usd_equivalent(st, per_model):
    total = 0.0
    for m, u in per_model.items():
        rate = st.rates.get(m)
        if not rate:
            continue
        i, o = rate
        total += (u["input_tokens"] * i + u["output_tokens"] * o
                  + u["cache_creation_input_tokens"] * i * 1.25
                  + u["cache_read_input_tokens"] * i * 0.1) / 1e6
    return total


def refresh_cost_numbers(st, ledger):
    """Replace <span data-ledger="..."> contents in cost/index.html."""
    path = os.path.join(st.site, "cost", "index.html")
    if not os.path.exists(path):
        return
    html = open(path).read()
    cats = ledger["categories"]

    def cat_vals(cat):
        c = cats[cat]
        return {
            "processed": comma(c["processed_tokens"]),
            "processed_b": "%.2f billion" % (c["processed_tokens"] / 1e9),
            "processed_m": "%d million" % round(c["processed_tokens"] / 1e6),
            "non_cache": comma(c["non_cache_tokens"]),
            "non_cache_m": "%d million" % round(c["non_cache_tokens"] / 1e6),
            "sessions": str(c["session_count"]),
            "first": c["first_ts"][:10],
            "last": c["last_ts"][:10],
            "usd": "$%s" % comma(int(round(usd_equivalent(st, c["per_model"]), -2))),
        }

    values = {}
    for cat in cats:
        for k, v in cat_vals(cat).items():
            values["%s.%s" % (cat, k)] = v
    values["generated"] = ledger["generated_utc"]
    values["%s.messages" % st.cfg["session_name_prefixes"][st.category]] = comma(
        sum(len(load_json(p)["msgs"]) for p in
            glob.glob(os.path.join(st.site, "content",
                                   st.category + "__session_*.json"))))

    def sub(m):
        key = m.group(1)
        if key not in values:
            return m.group(0)
        return '<span data-ledger="%s">%s</span>' % (key, values[key])
    html = re.sub(r'<span data-ledger="([^"]+)">.*?</span>', sub, html, flags=re.S)
    with open(path, "w") as fh:
        fh.write(html)


def main():
    rc = load(sys.argv[1:])
    configure(rc.get("sanitize"))
    st = Site(rc)
    ledger = load_json(os.path.join(st.work, "ledger.json"))
    summary = load_json(os.path.join(st.clean, "summary.json"))

    content_keys = write_content(st, summary)
    data = patch_data_js(st, summary)
    patch_manifest(st, summary, content_keys, data)
    patch_index(st)
    build_session_ledger(st, ledger)
    refresh_cost_numbers(st, ledger)
    print("content files:", len(content_keys))
    print("public_records:", data["census"]["public_records"],
          "assistant msgs:", data["census"]["message_roles"]["assistant"])
    print("tmax:", data["tmax"])


if __name__ == "__main__":
    main()

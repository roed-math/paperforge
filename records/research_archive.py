#!/usr/bin/env python3
"""Bundle published record content files into download archives.

Each configured bundle is byte-identical to what the site serves under
content/ and deterministic (sorted members, zeroed metadata, gzip mtime 0 —
same inputs, same sha256), so re-running is a no-op unless the published
content files themselves changed.  Counts and shas land in
corpora/manifest.json under the configured keys.

Config block ("research_archives"):

    {
      "corpus_stages": ["stage-id", ...],      # session-corpus stages
      "bundles": [
        {"name": "q2-research-records",
         "stage": null,                        # null -> every NON-corpus node
         "sha_key": "research_archive_sha256",
         "sources_key": "research_sources",    # optional {records, source}
         "sources_note": "...",
         "note_key": "...", "note": "..."      # optional manifest note
        }, ...
      ]
    }

Usage:  python3 records/research_archive.py [records-config.json]
"""
import gzip
import hashlib
import io
import json
import os
import re
import sys
import tarfile

from _config import load


def bundle(site_dev, archive_name, keys):
    """Deterministically tar+gzip content/<key>.json under archive_name/."""
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
        info = tarfile.TarInfo(archive_name)
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        tar.addfile(info)
        for key in keys:
            path = os.path.join(site_dev, "content", key + ".json")
            payload = open(path, "rb").read()
            info = tarfile.TarInfo(os.path.join(archive_name, key + ".json"))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            info.size = len(payload)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(payload))
    gz_path = os.path.join(site_dev, "corpora", archive_name + ".tar.gz")
    with open(gz_path, "wb") as fh:
        gz = gzip.GzipFile(fileobj=fh, mode="wb", mtime=0)
        gz.write(tar_bytes.getvalue())
        gz.close()
    sha = hashlib.sha256(open(gz_path, "rb").read()).hexdigest()
    print("wrote %s (%d records, %d bytes, sha256 %s)"
          % (gz_path, len(keys), os.path.getsize(gz_path), sha))
    return sha


def data_global(rc):
    return rc.get("apply_site", {}).get("data_global", "Q2DATA")


def main():
    rc = load(sys.argv[1:])
    cfg = rc["research_archives"]
    site_dev = rc.site_dev
    corpus_stages = set(cfg["corpus_stages"])

    text = open(os.path.join(site_dev, "data.js")).read()
    data = json.loads(re.match(
        r"^window\.%s\s*=\s*(.*?);?\s*\Z" % data_global(rc), text, re.S).group(1))

    manifest_path = os.path.join(site_dev, "corpora", "manifest.json")
    manifest = json.load(open(manifest_path))

    for b in cfg["bundles"]:
        if b.get("stage"):
            keys = sorted(n["key"] for n in data["nodes"]
                          if n.get("stage_id") == b["stage"])
        else:
            keys = sorted(n["key"] for n in data["nodes"]
                          if n.get("stage_id") not in corpus_stages)
        if not keys:
            raise SystemExit("no records found for bundle " + b["name"])
        sha = bundle(site_dev, b["name"], keys)
        manifest["inputs"][b["sha_key"]] = sha
        if b.get("sources_key"):
            manifest["inputs"][b["sources_key"]] = {
                "records": len(keys),
                "source": b["sources_note"],
            }
        if b.get("note_key"):
            manifest["inputs"][b["note_key"]] = b["note"]

    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()

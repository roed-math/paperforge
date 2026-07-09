#!/usr/bin/env python3
"""fetch_arxiv_corpus: download an author's arXiv papers (LaTeX source) into a
style-corpus directory.

Style corpora want .tex, not PDF (see templates/style-corpus/README.md). For
each paper by the author: fetch the e-print tarball, extract only text-ish
files (.tex/.bbl/.bib), and write style-corpus/arxiv/<id>/. Papers whose
e-print is PDF-only are saved as PDF (flagged in the manifest). A MANIFEST.md
records title/authors/year/id per paper.

Polite by design: one request every ~3s per arXiv guidelines.
"""
from __future__ import annotations

import argparse
import gzip
import io
import re
import tarfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ATOM = "{http://www.w3.org/2005/Atom}"
API = "http://export.arxiv.org/api/query"
UA = {"User-Agent": "paperforge-corpus-fetch/0.1 (mailto:roed.math@gmail.com)"}


def api_entries(author: str, max_results: int = 200):
    q = urllib.parse.urlencode({
        "search_query": f'au:"{author}"',
        "start": 0, "max_results": max_results,
        "sortBy": "submittedDate", "sortOrder": "descending"})
    with urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers=UA),
                                timeout=60) as r:
        feed = ET.fromstring(r.read())
    for e in feed.findall(f"{ATOM}entry"):
        # keep old-style archive prefixes intact: .../abs/math/0601508v2
        arxiv_id = e.find(f"{ATOM}id").text.split("/abs/", 1)[-1]
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        yield {
            "id": arxiv_id,
            "title": " ".join(e.find(f"{ATOM}title").text.split()),
            "authors": [a.find(f"{ATOM}name").text
                        for a in e.findall(f"{ATOM}author")],
            "year": (e.find(f"{ATOM}published").text or "????")[:4],
        }


def fetch_eprint(arxiv_id: str) -> bytes:
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=120) as r:
        return r.read()


def save_source(blob: bytes, dest: Path) -> str:
    """Unpack an e-print blob; returns 'tex' | 'single-tex' | 'pdf'."""
    dest.mkdir(parents=True, exist_ok=True)
    if blob[:5] == b"%PDF-":
        (dest / "paper.pdf").write_bytes(blob)
        return "pdf"
    try:
        data = gzip.decompress(blob)
    except OSError:
        data = blob
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            n = 0
            for m in tar.getmembers():
                if m.isfile() and Path(m.name).suffix.lower() in (
                        ".tex", ".bbl", ".bib", ".sty", ".cls"):
                    safe = re.sub(r"[^A-Za-z0-9._-]", "_",
                                  Path(m.name).name)
                    (dest / safe).write_bytes(tar.extractfile(m).read())
                    n += 1
            return "tex" if n else "pdf"
    except tarfile.TarError:
        if data[:5] == b"%PDF-":
            (dest / "paper.pdf").write_bytes(data)
            return "pdf"
        (dest / "paper.tex").write_bytes(data)   # single gzipped tex file
        return "single-tex"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("author", help='e.g. "David Roe"')
    ap.add_argument("--dest", type=Path, default=Path("style-corpus/arxiv"))
    ap.add_argument("--sleep", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entries = [e for e in api_entries(args.author)
               if args.author in e["authors"]]
    print(f"{len(entries)} paper(s) with '{args.author}' in the author list")
    manifest = ["# Style corpus: arXiv papers", "",
                f"Author query: {args.author}", ""]
    for e in entries:
        kind = "(dry-run)"
        if not args.dry_run:
            time.sleep(args.sleep)
            try:
                kind = save_source(fetch_eprint(e["id"]),
                                   args.dest / e["id"].replace("/", "_"))
            except Exception as exc:
                kind = f"FAILED: {exc}"
        print(f"  [{kind:10}] {e['id']:14} {e['title'][:70]}")
        manifest.append(
            f"- **{e['title']}** — {', '.join(e['authors'])} "
            f"({e['year']}) — `{e['id']}` — {kind}")
    if not args.dry_run:
        args.dest.mkdir(parents=True, exist_ok=True)
        (args.dest / "MANIFEST.md").write_text("\n".join(manifest) + "\n")
        print(f"manifest: {args.dest / 'MANIFEST.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

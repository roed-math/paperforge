#!/usr/bin/env python3
"""paperforge review server: an author-facing UI over the decision artifacts.

The pipeline's judgment calls live in committed JSON artifacts (novelty
claims, notation disambiguation, citation needs, formalized-known). Editing
JSON by hand is a poor review experience; this serves a dashboard where each
pending item is a card with the evidence, links into the *built paper*
(anchors resolve into output/web, so notation hovers and lean badges are one
click away), status buttons, and a note box. Decisions write back into the
native artifact files immediately — the same files the pipeline reads, so
there is no second source of truth.

Run from the instance root:    python3 <paperforge>/review/review_server.py
Then open the printed URL. Stdlib only; no dependencies.
"""
from __future__ import annotations

import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- anchors

def tag_href(tag: str) -> str | None:
    """Resolve a paper tag to a /paper/... URL via the numbering database."""
    numbering = ROOT / "crosswalk" / "numbering-current.json"
    if not hasattr(tag_href, "_items"):
        tag_href._items = (json.load(open(numbering))["items"]
                           if numbering.exists() else {})
    items = tag_href._items
    rec = items.get(tag)
    if rec is None:
        return None
    if rec["kind"] in ("section", "appendix"):
        return f"/paper/{tag}.html"
    sec = rec.get("section")
    for t, r in items.items():
        if r["kind"] in ("section", "appendix") and r["number"] == sec:
            return f"/paper/{t}.html#{tag}"
    return None


def links_for(tags) -> list[dict]:
    out = []
    for t in tags or []:
        href = tag_href(t)
        if href:
            out.append({"label": t, "href": href})
    return out


# ---------------------------------------------------------------- adapters
# Each adapter: items() -> [{id, title, body, links, status, choices, note,
# text (optional editable statement)}]; decide(id, status, note, text) writes
# back into the native artifact.

class Novelty:
    name = "novelty"
    label = "Novelty claims"
    path = ROOT / "novelty" / "claims.json"
    choices = ["proposed", "author-approved", "author-rejected",
               "needs-discussion"]

    def items(self):
        if not self.path.exists():
            return []
        data = json.load(open(self.path))["claims"]
        out = []
        for cid, c in data.items():
            body = "<br>".join(
                [f"<b>class {c['cls']}</b> · confidence: {c.get('confidence','?')}"]
                + [f"• {e}" for e in c.get("evidence", [])]
                + ([f"<i>hedge: {c['hedge']}</i>"] if c.get("hedge") else []))
            out.append(dict(id=cid, title=cid, body=body,
                            links=links_for(c.get("paper_anchors")),
                            status=c["status"], choices=self.choices,
                            note=c.get("author_note", ""),
                            text=c["statement"]))
        return out

    def decide(self, iid, status, note, text):
        data = json.load(open(self.path))
        c = data["claims"][iid]
        if status:
            c["status"] = status
        if note is not None:
            c["author_note"] = note
        if text is not None:
            c["statement"] = text
        json.dump(data, open(self.path, "w"), indent=1)


class Disambig:
    name = "disambig"
    label = "Notation senses"
    path = ROOT / "notation" / "disambiguation.json"
    map_path = ROOT / "notation" / "notation-map.json"

    def items(self):
        if not self.path.exists():
            return []
        data = json.load(open(self.path))
        senses = {}
        if self.map_path.exists():
            m = json.load(open(self.map_path))
            for k, rec in m.items():
                if rec.get("kind") == "ambiguous":
                    senses[k] = list(rec["senses"]) + ["none"]
        out = []
        for key, blocks in data.items():
            for block, sense in sorted(blocks.items()):
                out.append(dict(
                    id=f"{key}@{block}", title=f"{key} in {block}",
                    body=f"current sense: <b>{sense}</b>",
                    links=links_for([block]),
                    status=sense, choices=senses.get(key, [sense, "none"]),
                    note="", text=None))
        return out

    def decide(self, iid, status, note, text):
        key, block = iid.split("@", 1)
        data = json.load(open(self.path))
        if status:
            data[key][block] = status
        json.dump(data, open(self.path, "w"), indent=1)


class CitationNeeds:
    name = "citations"
    label = "Citation needs"
    path = ROOT / "references" / "citation-needs.json"
    choices = ["needs-citation", "cited-nearby", "common-knowledge"]

    def items(self):
        if not self.path.exists():
            return []
        data = json.load(open(self.path))
        out = []
        for group in ("axiom-driven", "named-results"):
            for iid, rec in data.get(group, {}).items():
                body = " · ".join(f"{k}: {v}" for k, v in rec.items()
                                  if k not in ("decision",))
                tag = iid.split("#")[0]
                out.append(dict(id=f"{group}|{iid}", title=iid, body=body,
                                links=links_for([tag]),
                                status=rec.get("decision", "?"),
                                choices=self.choices,
                                note=rec.get("author_note", ""), text=None))
        return out

    def decide(self, iid, status, note, text):
        group, key = iid.split("|", 1)
        data = json.load(open(self.path))
        rec = data[group][key]
        if status:
            rec["decision"] = status
        if note is not None:
            rec["author_note"] = note
        json.dump(data, open(self.path, "w"), indent=1)


class Known:
    name = "known"
    label = "Formalized-known"
    path = ROOT / "references" / "formalized-known.json"
    choices = ["known", "known-definition", "known-variant", "novel",
               "uncertain"]

    def items(self):
        if not self.path.exists():
            return []
        data = json.load(open(self.path))["decisions"]
        out = []
        for decl, rec in data.items():
            body = "<br>".join(f"{k}: {v}" for k, v in rec.items()
                               if k not in ("status",))
            out.append(dict(id=decl, title=decl.split(".")[-1], body=body,
                            links=[], status=rec["status"],
                            choices=self.choices,
                            note=rec.get("author_note", ""), text=None))
        return out

    def decide(self, iid, status, note, text):
        data = json.load(open(self.path))
        rec = data["decisions"][iid]
        if status:
            rec["status"] = status
        if note is not None:
            rec["author_note"] = note
        json.dump(data, open(self.path, "w"), indent=1)


ADAPTERS = {a.name: a() for a in (Novelty, Disambig, CitationNeeds, Known)}


# ---------------------------------------------------------------- server

class Handler(SimpleHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/review"):
            html = (HERE / "dashboard.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path.startswith("/api/artifacts"):
            return self._json([{"name": a.name, "label": a.label,
                                "count": len(a.items())}
                               for a in ADAPTERS.values()])
        m = re.match(r"/api/items\?artifact=(\w+)", self.path)
        if m and m.group(1) in ADAPTERS:
            return self._json(ADAPTERS[m.group(1)].items())
        if self.path.startswith("/paper/"):
            self.path = "/output/web/" + self.path[len("/paper/"):]
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/decide":
            return self._json({"error": "unknown endpoint"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        a = ADAPTERS.get(req.get("artifact"))
        if not a:
            return self._json({"error": "unknown artifact"}, 400)
        try:
            a.decide(req["id"], req.get("status"), req.get("note"),
                     req.get("text"))
        except KeyError as e:
            return self._json({"error": f"unknown item {e}"}, 400)
        return self._json({"ok": True})

    def log_message(self, *a):  # quiet
        pass


def main() -> int:
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 partial(Handler, directory=str(ROOT)))
    print(f"paperforge review: http://127.0.0.1:{port}/review")
    print(f"instance: {ROOT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

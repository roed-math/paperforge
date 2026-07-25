#!/usr/bin/env python3
"""prose_terms: wrap tracked prose terms with <termref> hover links.

The prose companion of the math notation wrap (tex2ptx --notation-map).
Scans the GENERATED PreTeXt tree (source/*.ptx, in main.ptx reading order)
and wraps occurrences of authored term patterns in

    <termref key="KEY">matched text</termref>

which the custom XSL renders as <span class="ptxnotn-KEY ptxbg"> in HTML
(hover popup wired by detail-ui.js from the same registry as math notation,
with the longer "far" delay) and as plain text in the LaTeX conversions.

Map file: paper.toml [notation] prose_map (default notation/prose-map.json):

    "bgArf": {
      "label": "Quadratic forms over F2",   # popup heading (else the key)
      "match": "Arf invariants?",           # regex over prose (see below)
      "scope": ["sec-quadratic"],           # optional division/block allowlist
      "first_per": "block",                 # block (default) | division | all
      "href": "bg-quadratic-f2",            # popup context-link target xml:id
      "definition": "popup html"            # consumed by notation_registry.py
    }
    (underscore keys are file metadata and are skipped)

Pattern language: Python regex matched against a masked "logical text" of
each file, in which every XML tag is an opaque barrier character except

    <ndash/> -> "–"    <mdash/> -> "—"    <nbsp/> -> " "

and an inline math element collapses to one atomic unit: write ``$H$`` in a
pattern to match a source ``<m>H</m>`` (the text between the ``$``s is
itself a regex applied to the element's content). A literal space in a
pattern matches any whitespace run. A match can never cross an element
boundary, so the inserted wrapper always nests properly; a match that only
partially covers a math element is discarded.

Skipped entirely: math displays, titles, xrefs, code, biblio, docinfo, the
existing <termref> wrappers (idempotence: their keys still count toward the
first-per-block bookkeeping), and any division file whose root id starts
with ``bg-`` (the background appendix must not link to itself).

Run AFTER tex2ptx + notation_far (insertion content exists only in the
generated tree; far word-counts are computed on the unwrapped text) and
BEFORE ``pretext build``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:      # Python < 3.11
    import tomli as tomllib
from pathlib import Path

# logical-text sentinels (private use area)
MOPEN, MCLOSE, BARRIER = "", "", ""

# elements whose content is never matched (atomic in the logical text);
# <m> is special-cased to stay matchable via the $...$ pattern syntax
SKIP = {"me", "men", "md", "mdn", "title", "xref", "url", "c", "cd", "pre",
        "lean", "termref", "idx", "docinfo", "macros", "biblio", "notation",
        "latex-image", "tabular"}

TOKEN = re.compile(r"<!--.*?-->|<[^>]*>", re.S)
NAME = re.compile(r"</?\s*([A-Za-z][\w:-]*)")
XMLID = re.compile(r"xml:id=\"([^\"]*)\"")
KEYATTR = re.compile(r"\bkey=\"([^\"]*)\"")
INCLUDE = re.compile(r"<xi:include\s+href=\"\./([^\"]+)\"")


def compile_pattern(src: str) -> re.Pattern:
    """Authored pattern -> regex over the logical text.

    ``$inner$`` segments become an atomic math unit (MOPEN inner MCLOSE);
    a literal space becomes any whitespace run (paragraph line wraps);
    the whole pattern gets word-boundary guards, so ``semisimple`` never
    fires inside ``nonsemisimple`` (hyphens/dashes still count as
    boundaries: compound exclusions need their own lookbehinds).
    """
    parts = re.split(r"(?<!\\)\$(.*?)(?<!\\)\$", src)
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(MOPEN + part + MCLOSE)
        else:
            out.append(part.replace(" ", r"(?:\s| )+"))
    return re.compile("(?<![A-Za-z])(?:" + "".join(out) + ")(?![A-Za-z])")


class Doc:
    """Logical text of one .ptx file + per-char structure maps."""

    def __init__(self, raw: str, seen: dict):
        self.raw = raw
        self.chars: list[str] = []
        self.starts: list[int] = []      # raw offset a match may open at
        self.ends: list[int] = []        # raw offset a match may close at
        self.unit: list[int] = []        # atomicity: shared id = same unit
        self.block: list[str] = []       # innermost xml:id
        self.ids: list[frozenset] = []   # all enclosing xml:ids (scope)
        self.root = ""                   # first xml:id (division tag)
        self._scan(seen)

    def _push_char(self, ch, a, b, uid, blk, ids):
        self.chars.append(ch)
        self.starts.append(a)
        self.ends.append(b)
        self.unit.append(uid)
        self.block.append(blk)
        self.ids.append(ids)

    def _scan(self, seen: dict) -> None:
        raw = self.raw
        stack: list[tuple[str, str | None]] = []
        cache_ids = frozenset()
        cache_blk = ""

        def refresh():
            nonlocal cache_ids, cache_blk
            found = [i for _, i in stack if i]
            cache_ids = frozenset(found)
            cache_blk = found[-1] if found else ""

        uid = 0
        pos = 0
        n = len(raw)
        while pos < n:
            m = TOKEN.search(raw, pos)
            upto = m.start() if m else n
            for k in range(pos, upto):     # plain text: one unit per char
                uid += 1
                self._push_char(raw[k], k, k + 1, uid, cache_blk, cache_ids)
            if not m:
                break
            tok = m.group(0)
            ts, te = m.start(), m.end()
            uid += 1
            if tok.startswith("<!--"):
                self._push_char(BARRIER, ts, te, uid, cache_blk, cache_ids)
                pos = te
                continue
            nm = NAME.match(tok)
            name = nm.group(1) if nm else ""
            closing = tok.startswith("</")
            selfclosing = tok.endswith("/>")
            if selfclosing and name in ("ndash", "mdash", "nbsp"):
                ch = {"ndash": "–", "mdash": "—", "nbsp": " "}[name]
                self._push_char(ch, ts, te, uid, cache_blk, cache_ids)
                pos = te
                continue
            if not closing and not selfclosing and name == "m":
                end = raw.find("</m>", te)
                if end < 0:
                    self._push_char(BARRIER, ts, te, uid, cache_blk, cache_ids)
                    pos = te
                    continue
                elem_end = end + len("</m>")
                self._push_char(MOPEN, ts, ts, uid, cache_blk, cache_ids)
                for k in range(te, end):
                    self._push_char(raw[k], k, k + 1, uid, cache_blk, cache_ids)
                self._push_char(MCLOSE, elem_end, elem_end, uid,
                                cache_blk, cache_ids)
                pos = elem_end
                continue
            if not closing and not selfclosing and name in SKIP:
                # opaque element: one barrier char spans it whole (none of
                # the skip elements nests inside itself, so first close wins)
                if name == "termref":
                    km = KEYATTR.search(tok)
                    if km:
                        seen[(km.group(1), cache_blk)] = \
                            seen.get((km.group(1), cache_blk), 0) + 1
                close_at = raw.find(f"</{name}>", te)
                elem_end = (close_at + len(f"</{name}>")
                            if close_at >= 0 else n)
                self._push_char(BARRIER, ts, elem_end, uid, cache_blk, cache_ids)
                pos = elem_end
                continue
            # structural tag: barrier char + stack bookkeeping
            self._push_char(BARRIER, ts, te, uid, cache_blk, cache_ids)
            if closing:
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == name:
                        del stack[k:]
                        break
                refresh()
            elif not selfclosing:
                idm = XMLID.search(tok)
                xid = idm.group(1) if idm else None
                if name == "abstract" and not xid:
                    xid = "abstract"
                stack.append((name, xid))
                if xid and not self.root:
                    self.root = xid
                refresh()
            pos = te

        self.text = "".join(self.chars)

    def boundary_ok(self, a: int, b: int) -> bool:
        """[a, b) starts at a unit start and ends at a unit end."""
        if a >= b:
            return False
        if a > 0 and self.unit[a] == self.unit[a - 1]:
            return False
        if b < len(self.unit) and self.unit[b - 1] == self.unit[b]:
            return False
        # never wrap a match that is only a barrier / whitespace
        body = self.text[a:b]
        return any(ch not in (BARRIER, MOPEN, MCLOSE) and not ch.isspace()
                   for ch in body)


def wrap_file(path: Path, entries: list, seen: dict, report: dict) -> int:
    raw = path.read_text()
    doc = Doc(raw, seen)
    if doc.root.startswith("bg-"):
        return 0                      # the background appendix itself
    accepted: list[tuple[int, int, str]] = []

    def overlaps(a, b):
        return any(not (b <= x or y <= a) for x, y, _ in accepted)

    for key, pat, scope, first_per in entries:
        for m in pat.finditer(doc.text):
            a, b = m.start(), m.end()
            if not doc.boundary_ok(a, b) or overlaps(a, b):
                continue
            if scope is not None and not (
                    doc.root in scope or (doc.ids[a] & scope)):
                continue
            if first_per == "division":
                dedup = (key, doc.root)
            elif first_per == "all":
                dedup = None
            else:
                dedup = (key, doc.block[a] or doc.root)
            if dedup is not None:
                if seen.get(dedup):
                    continue
                seen[dedup] = 1
            accepted.append((a, b, key))
            report.setdefault(key, {}).setdefault(path.name, []).append(
                re.sub(r"\s+", " ", doc.text[a:b]).replace(MOPEN, "$")
                .replace(MCLOSE, "$").replace(BARRIER, "|"))

    if not accepted:
        return 0
    # splice, back to front (matches never overlap)
    out = raw
    for a, b, key in sorted(accepted, key=lambda t: -doc.starts[t[0]]):
        ro, rc = doc.starts[a], doc.ends[b - 1]
        out = (out[:ro] + f'<termref key="{key}">' + out[ro:rc]
               + "</termref>" + out[rc:])
    path.write_text(out)
    return len(accepted)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", type=Path, nargs="?", default=Path.cwd())
    ap.add_argument("--map", type=Path, help="override prose map path")
    ap.add_argument("--report", type=Path,
                    help="write per-key wrap report JSON (coverage checks)")
    args = ap.parse_args()
    root = args.instance

    with open(root / "paper.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    ncfg = cfg.get("notation", {})
    map_path = args.map or root / ncfg.get("prose_map",
                                           "notation/prose-map.json")
    if not map_path.exists():
        print(f"prose_terms: no map at {map_path}; nothing to do")
        return 0
    raw_map = {k: v for k, v in json.load(open(map_path)).items()
               if not k.startswith("_")}
    entries = []
    for key, rec in raw_map.items():
        if not re.fullmatch(r"[A-Za-z0-9]+", key):
            print(f"WARNING: prose key '{key}' is not alphanumeric "
                  f"(detail-ui keyOf will not match it)", file=sys.stderr)
        entries.append((key, compile_pattern(rec["match"]),
                        frozenset(rec["scope"]) if rec.get("scope") else None,
                        rec.get("first_per", "block"),
                        len(rec["match"])))
    entries.sort(key=lambda t: (-t[4], t[0]))
    entries = [(k, p, s, f) for k, p, s, f, _ in entries]

    source = root / "source"
    main_ptx = source / "main.ptx"
    files = [main_ptx] + [source / h
                          for h in INCLUDE.findall(main_ptx.read_text())]
    seen: dict = {}
    report: dict = {}
    total = 0
    for f in files:
        if not f.exists():
            continue
        n = wrap_file(f, entries, seen, report)
        if n:
            print(f"  {f.name}: {n} term links")
        total += n
    unused = [k for k, *_ in entries if k not in report]
    if unused:
        print(f"WARNING: no occurrences wrapped for: {', '.join(sorted(unused))}",
              file=sys.stderr)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=1, sort_keys=True,
                                          ensure_ascii=False))
    print(f"prose_terms: {total} term links "
          f"({len(report)}/{len(entries)} keys used)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

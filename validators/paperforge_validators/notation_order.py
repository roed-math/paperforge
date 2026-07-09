"""Requirement 8: notation is defined before it is used.

Convention (see pretext-template/macros/README.md and the HTML hover layer):
every occurrence of tracked notation is written ``\\notn{key}{symbol}`` inside
math, and its *defining site* is one of

  1. a ``<notation>`` element whose ``@key`` attribute (preferred) or whose
     ``<usage>`` content names the key, placed where the notation is
     introduced — this also feeds PreTeXt's List of Notation; or
  2. failing that, the first ``\\notn{key}...`` occurrence that sits inside a
     ``<definition>`` block.

Walking the assembled document in reading order:

  - a ``\\notn`` use positioned BEFORE the key's defining site -> ERROR;
  - a key with uses but no defining site anywhere -> ERROR;
  - a defined key that is never used -> WARNING (stale notation entry).

Documents that do not use ``\\notn`` yet produce no findings — the check
activates as the notation-tagging pass introduces the convention.
"""
from __future__ import annotations

import re

from . import Finding
from ._document import MATH_TAGS, load_assembled, nearest_id, _localname

_NOTN = re.compile(r"\\notn\{([^}]*)\}")


def _inside_definition(el) -> bool:
    return any(isinstance(anc.tag, str) and _localname(anc) == "definition"
               for anc in el.iterancestors())


def _load_map(config: dict):
    """Optional notation map: defsite ids per key + standard exemptions."""
    import json
    from pathlib import Path
    from . import instance_root
    rel = config.get("notation", {}).get("map", "notation/notation-map.json")
    path = instance_root(config) / rel
    if not path.exists():
        return {}, set()
    entries = json.load(open(path))
    defsites = {k: r["defsite"] for k, r in entries.items() if r.get("defsite")}
    standard = {k for k, r in entries.items() if r.get("standard")}
    return defsites, standard


def check(config: dict) -> list[Finding]:
    try:
        root = load_assembled(config)
    except Exception as e:
        return [Finding("notation_order", "error", f"cannot assemble source: {e}")]

    map_defsites, standard = _load_map(config)
    findings: list[Finding] = []
    defined_at: dict[str, int] = {}              # key -> defining position
    uses: dict[str, list[tuple[int, str]]] = {}  # key -> [(pos, location-id)]
    id_pos: dict[str, int] = {}                  # xml:id -> position

    for pos, el in enumerate(root.iter()):
        if isinstance(el.tag, str):
            xid = el.get("{http://www.w3.org/XML/1998/namespace}id")
            if xid and xid not in id_pos:
                id_pos[xid] = pos
        tag = _localname(el)
        if tag is None:
            continue
        if tag == "notation":
            key = el.get("key")
            if not key:
                usage = el.find("usage")
                text = "".join(usage.itertext()) if usage is not None else ""
                m = _NOTN.search(text)
                key = m.group(1) if m else None
            if key:
                defined_at.setdefault(key, pos)
            else:
                findings.append(Finding(
                    "notation_order", "warning",
                    "<notation> without @key or \\notn in its <usage> — "
                    "cannot participate in order checking", nearest_id(el)))
        elif tag in MATH_TAGS:
            text = "".join(el.itertext())
            for m in _NOTN.finditer(text):
                key = m.group(1)
                uses.setdefault(key, []).append((pos, nearest_id(el)))
                # fallback defining site: first use inside a <definition>
                if key not in defined_at and _inside_definition(el):
                    defined_at[key] = pos

    # map-declared defining sites (resolved xml:id -> position); a map defsite
    # takes precedence over the fallback first-use-inside-<definition>
    for key, xid in map_defsites.items():
        if xid in id_pos:
            defined_at[key] = min(defined_at.get(key, id_pos[xid]), id_pos[xid])

    for key, sites in sorted(uses.items()):
        if key in standard:
            continue        # universally-known notation: hover only, no order gate
        if key not in defined_at:
            findings.append(Finding(
                "notation_order", "error",
                f"notation '{key}' used {len(sites)} time(s) but never defined "
                f"(no <notation key=\"{key}\"> and no use inside a <definition>)",
                sites[0][1]))
            continue
        early = [loc for pos, loc in sites if pos < defined_at[key]]
        if early:
            findings.append(Finding(
                "notation_order", "error",
                f"notation '{key}' used before its definition "
                f"({len(early)} early use(s))", early[0]))
    for key in sorted(set(defined_at) - set(uses) - standard):
        findings.append(Finding(
            "notation_order", "warning",
            f"notation '{key}' is defined but never used"))
    return findings

#!/usr/bin/env python3
"""Generate Verso blueprint chapters from the paper source + crosswalk.

Deterministic mirror of the paper into a verso-blueprint: every paper
statement with a Lean counterpart (crosswalk/lean-decl-map.json) becomes a
blueprint node whose prose IS the paper's statement (PreTeXt -> KaTeX),
``(lean := ...)`` lists the mapped declarations, and ``{uses}`` edges come
from the xrefs in the statement's proof plus the axiom census anchors. A
Foundations chapter renders the census (crosswalk/axiom-citations.json).

Re-run after re-ingestion or census changes; generated chapter files are
overwritten (hand-authored chapters with other names are left alone).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from lxml import etree

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
KINDS = {"theorem", "lemma", "proposition", "corollary", "definition"}

CHAPTER_HEADER = """\
import {module}
import Verso
import VersoManual
import VersoBlueprint

open Verso.Genre
open Verso.Genre.Manual
open Informal

{prelude}
#doc (Manual) "{title}" =>

"""


def clean_math(s: str) -> str:
    """Verbatim paper LaTeX -> KaTeX-safe: strip \\notn wrappers, collapse ws."""
    for macro in (r"\notnfar", r"\notn"):
        while True:
            i = s.find(macro + "{")
            if i < 0:
                break
            j = _brace(s, i + len(macro))          # end of {key}
            k = _brace(s, j + 1)                   # end of {payload}
            s = s[:i] + s[j + 2:k] + s[k + 1:]
    return re.sub(r"\s+", " ", s).strip()


def _brace(s: str, i: int) -> int:
    """Index of the brace closing the one at s[i]."""
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return j
    raise ValueError(f"unbalanced braces at {i}: {s[i:i+40]}")


class Gen:
    def __init__(self, root: Path, declmap="crosswalk/lean-decl-map.json",
                 census="crosswalk/axiom-citations.json",
                 atlas="crosswalk/atlas-graph.json", module="GQ2",
                 doc_title=None):
        self.root = root
        self.module = module
        self.doc_title = doc_title
        self.declmap = json.load(open(root / declmap))
        self.numbering = json.load(
            open(root / "crosswalk/numbering-current.json"))["items"]
        census_path = root / census if census and census != "none" else None
        self.census = (json.load(open(census_path))
                       if census_path and census_path.exists() else {})
        self._atlas = atlas
        self.nodes = set(self.declmap)          # blueprint labels = paper tags
        self.ax_label = {}
        taken = set()
        for name, rec in self.census.items():
            lab = "ax-" + re.sub(r"[^A-Za-z0-9]", "",
                                 (rec.get("census") or name.rsplit(".", 1)[-1])
                                 .replace("′", "p").replace("'", "p"))
            if lab in taken:      # e.g. two docstrings both marked B11
                lab += "-" + name.rsplit(".", 1)[-1].split("_")[0]
            taken.add(lab)
            self.ax_label[name] = lab
        # axiom edges: statement tag -> [axiom labels anchored there]
        self.ax_uses: dict[str, list[str]] = {}
        for name, rec in self.census.items():
            for t in rec.get("paper_tags", []):
                if t in self.nodes:
                    self.ax_uses.setdefault(t, []).append(self.ax_label[name])
        # Lean-derived dependency edges (the authoritative structure): BFS
        # from each node's declarations down the atlas graph (source depends
        # on target), stopping at the first declaration owned by another
        # blueprint node. Paper-prose xrefs alone leave the graph flat — the
        # main theorem's "proof" is the whole induction, so nothing reaches
        # it in prose.
        self.decl_label: dict[str, str] = {}
        for t, v in self.declmap.items():
            for e in v:
                self.decl_label[e["decl"]] = t
        for name, lab in self.ax_label.items():
            self.decl_label.setdefault(name, lab)
        self.lean_uses: dict[str, set[str]] = {}
        atlas = root / self._atlas if self._atlas else None
        if atlas and atlas.exists():
            g = json.load(open(atlas))
            deps: dict[str, list[str]] = {}
            for e in g["edges"]:
                deps.setdefault(e["source"], []).append(e["target"])
            for label in set(self.decl_label.values()):
                seeds = [d for d, l in self.decl_label.items() if l == label]
                seen, stack, found = set(seeds), list(seeds), set()
                while stack:
                    d = stack.pop()
                    for nxt in deps.get(d, ()):
                        if nxt in seen:
                            continue
                        seen.add(nxt)
                        lab = self.decl_label.get(nxt)
                        if lab and lab != label:
                            found.add(lab)     # edge; don't traverse through
                        else:
                            stack.append(nxt)
                self.lean_uses[label] = found

    @staticmethod
    def reduce_edges(uses: dict[str, set[str]]) -> dict[str, list[str]]:
        """Transitive reduction at node grain: drop a direct edge when the
        target is already reachable through another dependency (keeps the
        rendered graph layered instead of a shortcut-dense clique)."""
        def close(start: str, acc: set[str]) -> set[str]:
            for b in uses.get(start, ()):
                if b not in acc:
                    acc.add(b)
                    close(b, acc)
            return acc

        reduced: dict[str, list[str]] = {}
        for a, bs in uses.items():
            keep = []
            for b in sorted(bs):
                via_others: set[str] = set()
                for c in bs:
                    if c != b and c not in via_others:
                        via_others.add(c)
                        close(c, via_others)
                if b not in via_others:
                    keep.append(b)
            reduced[a] = keep
        return reduced

    # ---------------------------------------------------------- inline text
    @staticmethod
    def esc(s: str) -> str:
        """Escape Verso/markdown-active characters in raw prose text."""
        return re.sub(r"([`*_{}\[\]])", r"\\\1", s)

    def inline(self, el, math_wrap=True) -> str:
        out = [self.esc(el.text or "")]
        for ch in el:
            tag = etree.QName(ch).localname if isinstance(ch.tag, str) else ""
            if tag == "m":
                out.append(f"$`{clean_math(ch.text or '')}`")
            elif tag in ("me", "men"):
                out.append(f"\n\n$$`{clean_math(ch.text or '')}`\n\n")
            elif tag == "xref":
                out.append(self.xref(ch))
            elif tag == "nbsp":
                out.append(" ")
            elif tag == "ndash":
                out.append("–")
            elif tag == "mdash":
                out.append("—")
            elif tag == "em":
                out.append(f"*{self.inline(ch).strip()}*")
            elif tag == "c":
                out.append(f"`{(ch.text or '').strip()}`")
            elif tag == "alert":
                out.append(f"**{self.inline(ch).strip()}**")
            elif tag == "lean":
                pass                                  # badges: HTML feature
            else:
                out.append(self.inline(ch))
            out.append(self.esc(ch.tail or ""))
        return "".join(out)

    def plain(self, el) -> str:
        """Plain text (no Verso markup) — for #doc titles, which reject math."""
        out = [el.text or ""]
        for ch in el:
            out.append(self.plain(ch))
            out.append(ch.tail or "")
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def xref(self, ch) -> str:
        ref = ch.get("ref", "")
        if ref in self.nodes:
            return f'{{bpref "{ref}"}}[]'
        if ref.startswith("bib-"):
            pin = ch.get("detail")
            # \[ ... \]: literal brackets, not markdown link syntax
            return f"\\[{ref[4:]}{', ' + pin if pin else ''}\\]"
        rec = self.numbering.get(ref)
        if rec:
            n = rec["number"]
            if ref.startswith("eq-"):
                return n if n.startswith("(") else f"({n})"
            return f"{rec['kind'].capitalize()} {n}"
        return ref

    # ---------------------------------------------------------- blocks
    def prose(self, container) -> str:
        parts = []
        for ch in container:
            tag = etree.QName(ch).localname if isinstance(ch.tag, str) else ""
            if tag == "p":
                parts.append(re.sub(r"[ \t]+", " ", self.inline(ch)).strip())
            elif tag in ("ul", "ol"):
                items = []
                for k, li in enumerate([c for c in ch
                                        if etree.QName(c).localname == "li"], 1):
                    mark = "-" if tag == "ul" else f"{k}."
                    items.append(f"{mark} " +
                                 re.sub(r"\s+", " ", self.inline(li)).strip())
                parts.append("\n".join(items))
            elif tag in ("me", "men"):
                parts.append(f"$$`{clean_math(ch.text or '')}`")
        return "\n\n".join(p for p in parts if p)

    def proof_xref_uses(self, el, tag: str) -> list[str]:
        uses = []
        for proof in el.findall("proof"):
            for x in proof.iter("xref"):
                r = x.get("ref", "")
                if r in self.nodes and r != tag and r not in uses:
                    uses.append(r)
        return uses

    def node(self, el, tag: str, uses: list[str], group: str) -> str:
        rec = self.numbering[tag]
        kind = etree.QName(el).localname
        if kind not in KINDS:
            kind = rec["kind"] if rec["kind"] in KINDS else "proposition"
        decls = ", ".join(e["decl"] for e in self.declmap[tag])
        title_el = el.find("title")
        title = (" (" + re.sub(r"\s+", " ",
                               self.inline(title_el)).strip().rstrip(".") + ")"
                 if title_el is not None else "")
        stmt = el.find("statement")
        body = self.prose(stmt) if stmt is not None else ""
        # backlink into the interactive paper: Verso content pages all sit
        # one directory below the blueprint root, so ../../paper/ is stable
        head = (f"*[{rec['kind'].capitalize()} {rec['number']} of the "
                f"paper](../../paper/paper.html#{tag}){title}.*")
        # 'lemma' is a Lean keyword; VersoBlueprint registers the directive
        # with a trailing underscore
        directive = "lemma_" if kind == "lemma" else kind
        out = [f':::{directive} "{tag}" (lean := "{decls}") '
               f'(parent := "{group}")', head, "", body, ":::"]
        if uses:
            links = " ".join(f'{{uses "{u}"}}[]' for u in uses)
            out += ["", f':::proof "{tag}"',
                    f"Proved in §{rec['section']} of the paper. "
                    f"Ingredients: {links}.", ":::"]
        return "\n".join(out)

    # ---------------------------------------------------------- chapters
    def macros_prelude(self) -> str:
        main = (self.root / "source/main.ptx").read_text()
        m = re.search(r"<macros>(.*?)</macros>", main, re.S)
        lines = [ln.strip() for ln in (m.group(1) if m else "").splitlines()]
        keep = [ln for ln in lines
                if ln.startswith("\\newcommand") and "\\notn" not in ln]
        # escape for a Lean string literal (backslashes first, then quotes)
        blob = "".join(keep).replace("\\", "\\\\").replace('"', '\\"')
        return f'tex_prelude "{blob}"\n' if keep else ""

    def run(self, out_lib: Path, project: str) -> list[str]:
        main = (self.root / "source/main.ptx").read_text()
        order = re.findall(r'href="\./(sec-[^"]+|app-[^"]+)\.ptx"', main)
        prelude = self.macros_prelude()
        # pass 1: parse chapters, collect the union of edge sources per tag
        parsed = []
        all_uses: dict[str, set[str]] = {}
        for stem in order:
            f = self.root / "source" / f"{stem}.ptx"
            tree = etree.parse(str(f)).getroot()
            els = [(el.get(XML_ID), el) for el in tree.iter()
                   if el.get(XML_ID) in self.nodes]
            if not els:
                continue
            for t, el in els:
                all_uses[t] = (set(self.proof_xref_uses(el, t))
                               | set(self.ax_uses.get(t, []))
                               | self.lean_uses.get(t, set()))
                all_uses[t].discard(t)
            parsed.append((stem, tree, els))
        final = self.reduce_edges(all_uses)
        edge_count = sum(len(v) for v in final.values())
        # pass 2: emit
        chapters = []
        if self.census:
            chapters.append("Foundations")
            (out_lib / "Chapters/Foundations.lean").write_text(
                CHAPTER_HEADER.format(prelude=prelude, module=self.module,
                                      title="Foundational inputs")
                + self.foundations())
        for stem, tree, els in parsed:
            sec_title = (self.plain(tree.find("title"))
                         if tree.find("title") is not None else stem)
            name = "".join(w.capitalize() for w in
                           re.sub(r"^(sec|app)-", "", stem).split("-"))
            name = re.sub(r"[^A-Za-z0-9]", "", name) or "Chapter"
            group = f"ch-{name}"
            header = (f':::group "{group}"\n{self.esc(sec_title)}\n:::\n\n')
            body = "\n\n".join(self.node(el, t, final.get(t, []), group)
                               for t, el in els)
            (out_lib / "Chapters" / f"{name}.lean").write_text(
                CHAPTER_HEADER.format(prelude=prelude, module=self.module,
                                      title=sec_title)
                + header + body + "\n")
            chapters.append(name)
        self.blueprint_root(out_lib, project, chapters)
        print(f"edges after reduction: {edge_count} "
              f"(lean-derived: {sum(len(v) for v in self.lean_uses.values())})")
        return chapters

    def foundations(self) -> str:
        out = [":::group \"foundations\"",
               "The foundational inputs of the formalization: statements "
               "assumed as Lean axioms, each resting on the literature, plus "
               "former axioms since discharged by proofs.", ":::", ""]
        for name, rec in sorted(self.census.items(),
                                key=lambda kv: kv[1].get("census") or kv[0]):
            label = self.ax_label[name]
            short = name.rsplit(".", 1)[-1]
            cite = re.sub(r"\s+", " ", (rec.get("citation_lines") or [""])[0])
            cite = (cite[:220] + "…") if len(cite) > 220 else cite
            # citations are arbitrary docstring prose: escape all markdown
            cite = re.sub(r"([\\`*_{}\[\]<>$#])", r"\\\1", cite)
            status = rec.get("status", "axiom")
            if status == "discharged":
                desc = (f"*Former axiom {rec.get('census', '')} — now proved* "
                        f"(`{short}`, `{rec['file']}`).")
            else:
                desc = (f"*Foundational input {rec.get('census', '')}, assumed "
                        f"as a Lean axiom* (`{short}`, `{rec['file']}`).")
            anchors = " ".join(f'{{bpref "{t}"}}[]'
                               for t in rec.get("paper_tags", [])
                               if t in self.nodes)
            ptag = next(iter(rec.get("paper_tags", [])), None)
            if ptag:
                anchors += (f" — [see in the paper]"
                            f"(../../paper/paper.html#{ptag})")
            body = [f':::proposition "{label}" (lean := "{name}") '
                    f'(parent := "foundations") (tags := "{status}")',
                    desc, ""]
            if cite:
                body.append(f"Citation: {cite}")
            if anchors:
                body.append(f"\nUsed at: {anchors}.")
            body.append(":::")
            out.append("\n".join(body) + "\n")
        return "\n".join(out)

    def blueprint_root(self, out_lib: Path, project: str, chapters: list[str]):
        imports = "\n".join(f"import {project}.Chapters.{c}" for c in chapters)
        includes = "\n\n".join(f"{{include 0 {project}.Chapters.{c}}}"
                               for c in chapters)
        (out_lib / "Blueprint.lean").write_text(f"""\
import Verso
import VersoManual
import VersoBlueprint
import VersoBlueprint.Commands.Graph
import VersoBlueprint.Commands.Summary
{imports}

open Verso.Genre
open Verso.Genre.Manual
open Informal

#doc (Manual) "{self.doc_title or 'Blueprint'}" =>

This blueprint pairs every paper statement that has a formalized counterpart
with its Lean declarations, generated from the paper source and the
formalization crosswalk (paperforge `ingest/blueprint_gen.py`). Node status
is computed from the Lean declarations directly; edges follow the paper's
proofs{', the axiom census,' if self.census else ''} and the formalization's
own dependency graph.

{includes}

{{blueprint_graph}}

{{blueprint_summary}}
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", type=Path, nargs="?", default=Path.cwd())
    ap.add_argument("--blueprint-dir", type=Path, default=None,
                    help="blueprint project dir (default <instance>/blueprint)")
    ap.add_argument("--project", default="GQ2Blueprint")
    ap.add_argument("--declmap", default="crosswalk/lean-decl-map.json")
    ap.add_argument("--census", default="crosswalk/axiom-citations.json",
                    help="axiom census JSON, or 'none' to skip Foundations")
    ap.add_argument("--atlas", default="crosswalk/atlas-graph.json",
                    help="Lean Atlas graph export for dependency edges "
                         "(skipped when the file does not exist)")
    ap.add_argument("--module", default="GQ2",
                    help="Lean module the chapters import")
    ap.add_argument("--title", default="Blueprint: a profinite presentation "
                                       "of the absolute Galois group of ℚ₂")
    args = ap.parse_args()
    root = args.instance.resolve()
    bp = args.blueprint_dir or root / "blueprint"
    out_lib = bp / args.project
    (out_lib / "Chapters").mkdir(parents=True, exist_ok=True)
    gen = Gen(root, declmap=args.declmap, census=args.census,
              atlas=args.atlas, module=args.module, doc_title=args.title)
    chapters = gen.run(out_lib, args.project)
    print(f"wrote {len(chapters)} chapters -> {out_lib}/Chapters/ "
          f"(+ Blueprint.lean)")


if __name__ == "__main__":
    main()

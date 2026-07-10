#!/usr/bin/env python3
"""tex2ptx: deterministic LaTeX -> PreTeXt converter + numbering simulator.

The mechanical engine of the ingest-draft skill. Tuned for regular amsart-style
papers (sectioning, shared-counter theorem environments, equation/align display
math, no figures). Idempotent by design: the paper draft is a moving target, so
re-ingestion must be cheap and produce stable output (stable xml:ids = tags).

Two outputs from one parse:
  --out DIR         PreTeXt source tree (main.ptx + one file per section)
  --numbering FILE  JSON map: tag -> {kind, label, number, section} simulating
                    LaTeX's printed numbering for this version of the tex.

Tag system: xml:id is the canonical, restructuring-insensitive identity of every
numbered item. Tags derive from LaTeX labels (':' -> '-'); unlabeled numbered
items get generated tags and a warning (they are drift hazards).

Simulated numbering (amsart conventions of the gq2 paper):
  - sections: 1,2,... ; after \\appendix: A,B,...
  - one shared theorem-like counter (aliascnt), reset per section: "4.2"
  - equations: one GLOBAL counter; +1 per equation env and per align row
    without \\notag. "(59)"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

THEOREM_ENVS = ["theorem", "proposition", "lemma", "corollary", "claim",
                "definition", "remark"]
# PreTeXt element for each (statement-bearing blocks all share the same shape)
PTX_THM = {e: e for e in THEOREM_ENVS}
PTX_THM["claim"] = "claim"

WARN: list[str] = []


def warn(msg: str) -> None:
    WARN.append(msg)
    print(f"WARNING: {msg}", file=sys.stderr)


# ---------------------------------------------------------------- utilities

def tagify(label: str) -> str:
    """LaTeX label -> xml:id (NCName-safe stable tag)."""
    t = label.replace(":", "-").replace("_", "-")
    t = re.sub(r"[^A-Za-z0-9.\-]", "-", t)
    return t


def slugify(title: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+", "", title)          # drop macros
    s = re.sub(r"[${}^_]", "", s)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return "-".join(s.split("-")[:5]) or "untitled"


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;")


def find_env_end(text: str, start: int, env: str) -> int:
    """Index just past \\end{env}, honoring nesting of the same env."""
    depth = 1
    pat = re.compile(r"\\(begin|end)\{" + re.escape(env) + r"\}")
    for m in pat.finditer(text, start):
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            return m.end()
    raise ValueError(f"unterminated environment {env} at {start}")


def strip_comments(tex: str) -> str:
    """Remove % comments (not \\%), preserving line structure."""
    out = []
    for line in tex.split("\n"):
        i, prev = 0, ""
        while i < len(line):
            if line[i] == "%" and prev != "\\":
                line = line[:i]
                break
            prev = line[i]
            i += 1
        out.append(line)
    return "\n".join(out)


def split_rows(body: str) -> list[str]:
    r"""Split align body at top-level \\ (not inside nested \begin...\end)."""
    rows, depth, cur, i = [], 0, [], 0
    while i < len(body):
        m = re.match(r"\\(begin|end)\{[a-zA-Z*]+\}", body[i:])
        if m:
            depth += 1 if m.group(1) == "begin" else -1
            cur.append(m.group(0))
            i += m.end()
            continue
        if depth == 0 and body.startswith(r"\\", i):
            rows.append("".join(cur))
            cur = []
            i += 2
            # swallow optional spacing arg like \\[2pt]
            sp = re.match(r"\[[^\]]*\]", body[i:])
            if sp:
                i += sp.end()
            continue
        cur.append(body[i])
        i += 1
    last = "".join(cur)
    if last.strip():
        rows.append(last)
    return rows


# ---------------------------------------------------------------- numbering

@dataclass
class Numbering:
    section: int | str = 0
    in_appendix: bool = False
    thm: int = 0
    eq: int = 0
    subsec: int = 0
    records: dict = field(default_factory=dict)

    def enter_section(self) -> str:
        if self.in_appendix:
            if isinstance(self.section, str) and len(self.section) == 1 \
                    and self.section.isalpha():
                self.section = chr(ord(self.section) + 1)
            else:
                self.section = "A"
        else:
            self.section = (self.section or 0) + 1
        self.thm = 0
        self.subsec = 0
        return str(self.section)

    def next_subsec(self) -> str:
        self.subsec += 1
        return f"{self.section}.{self.subsec}"

    def next_thm(self) -> str:
        self.thm += 1
        return f"{self.section}.{self.thm}"

    def next_eq(self) -> str:
        self.eq += 1
        return f"({self.eq})"

    def record(self, tag: str, kind: str, label: str | None, number: str) -> None:
        self.records[tag] = {"kind": kind, "label": label, "number": number,
                             "section": str(self.section)}


# ---------------------------------------------------------------- inline text

LABEL_RE = re.compile(r"\\label\{([^}]*)\}")

# key -> (regex, scope). Set from --notation-map; applied to every piece of
# math through convert_math (the single funnel), so wrapping is idempotent by
# construction: the tex input never contains \notn. A "scope" entry limits
# wrapping to the named top-level divisions (for symbols like a bare Y whose
# meaning is section-dependent).
NOTATION_WRAPS: list[tuple[str, re.Pattern, frozenset | None]] = []
_CURRENT_DIVISION: list[str] = [""]     # tag of the division being converted
_CURRENT_BLOCK: list[str] = [""]        # theorem-like tag, else the division

# Ambiguous single-letter notation: the same letter means different things in
# different places (Y = boundary-framed ambient vs Demushkin generator), which
# no regex can resolve. Map entries with kind="ambiguous" carry a `senses`
# table; per-BLOCK sense decisions live in a committed cache
# (notation/disambiguation.json) produced by an LLM classification pass.
# Unclassified (key, block) pairs are left UNWRAPPED (safe default) and
# reported to a worklist file for incremental classification.
AMBIG_WRAPS: list[tuple[str, re.Pattern, dict]] = []   # (key, regex, senses)
DISAMBIG: dict = {}                                    # key -> {block: sense}
UNCLASSIFIED: dict = {}                                # (key, block) -> [ctx]

# --mathbb: restyle bold number-system letters to blackboard bold.
MATHBB_LETTERS: str = ""
_MATHBB_RE: re.Pattern | None = None


_CURRENT_SECTION: list[str] = [""]      # top-level division (scope matching)


def set_division(tag: str) -> None:
    """Enter a top-level division (section/appendix)."""
    _CURRENT_SECTION[0] = tag
    _CURRENT_DIVISION[0] = tag
    _CURRENT_BLOCK[0] = tag


def set_subdivision(tag: str) -> None:
    """Enter a subsection: finer block grain, same top-level scope."""
    _CURRENT_DIVISION[0] = tag
    _CURRENT_BLOCK[0] = tag


def set_block(tag: str) -> None:
    _CURRENT_BLOCK[0] = tag


def set_mathbb(letters: str) -> None:
    global MATHBB_LETTERS, _MATHBB_RE
    MATHBB_LETTERS = letters
    if letters:
        # match \mathbf{Q} or \mathbf Q — a closing brace is consumed ONLY
        # when the matching opening brace was (conditional group), else a
        # brace belonging to an enclosing group would be eaten.
        _MATHBB_RE = re.compile(
            r"\\mathbf\s*(\{)?([" + letters + r"])(?(1)\})")


def load_notation_wraps(map_path: Path, disambig_path: Path | None = None) -> None:
    entries = json.load(open(map_path))
    wraps = []
    for key, rec in entries.items():
        if rec.get("kind") == "ambiguous":
            AMBIG_WRAPS.append((key, re.compile(rec["match"]), rec["senses"]))
            continue
        if rec.get("kind") == "macro":
            pat = re.escape(rec["match"]) + r"(?![a-zA-Z])"
        else:
            pat = rec["match"]          # authored regex, trusted
        scope = frozenset(rec["scope"]) if rec.get("scope") else None
        wraps.append((key, re.compile(pat), scope, len(rec["match"])))
    # longest match string first, so \WA never loses to a shorter prefix
    wraps.sort(key=lambda t: -t[3])
    NOTATION_WRAPS.extend((k, p, s) for k, p, s, _ in wraps)
    if disambig_path and disambig_path.exists():
        # underscore keys are file metadata (_generator, _comment), not letters
        DISAMBIG.update({k: v for k, v in json.load(open(disambig_path)).items()
                         if not k.startswith("_")})


def convert_math(s: str) -> str:
    """Math content: verbatim LaTeX (restyled + notation-wrapped), XML-escaped."""
    s = s.strip()
    if _MATHBB_RE is not None:
        s = _MATHBB_RE.sub(r"\\mathbb{\2}", s)
    for key, pat, scope in NOTATION_WRAPS:
        if scope is not None and _CURRENT_DIVISION[0] not in scope \
                and _CURRENT_SECTION[0] not in scope:
            continue
        s = pat.sub(lambda m, k=key: "\\notn{%s}{%s}" % (k, m.group(0)), s)
    block = _CURRENT_BLOCK[0]
    for key, pat, senses in AMBIG_WRAPS:
        decision = DISAMBIG.get(key, {}).get(block)
        if decision in senses:
            s = pat.sub(lambda m, k=decision: "\\notn{%s}{%s}" % (k, m.group(0)), s)
        elif decision is None:
            for m in pat.finditer(s):
                ctx = s[max(0, m.start() - 40):m.end() + 40]
                UNCLASSIFIED.setdefault(key, {}).setdefault(block, []).append(ctx)
        # decision == "none": deliberate no-wrap
    return xml_escape(s)


def convert_inline(s: str, refs: "RefMap") -> str:
    """Convert a run of paragraph-level LaTeX to PreTeXt inline markup."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "$":
            j = i + 1
            while j < n and (s[j] != "$" or s[j - 1] == "\\"):
                j += 1
            out.append("<m>" + convert_math(s[i + 1:j]) + "</m>")
            i = j + 1
            continue
        if s.startswith(r"\[", i):
            j = s.index(r"\]", i)
            out.append("<me>" + convert_math(s[i + 2:j]) + "</me>")
            i = j + 2
            continue
        if s.startswith(r"\(", i):
            j = s.index(r"\)", i)
            out.append("<m>" + convert_math(s[i + 2:j]) + "</m>")
            i = j + 2
            continue
        if s.startswith(r"\S", i) and not re.match(r"\\S[a-zA-Z]", s[i:]):
            out.append("&#xa7;")
            i += 2
            continue
        m = re.match(r"\\renewcommand\{\\arraystretch\}\{[^}]*\}", s[i:])
        if m:
            i += m.end()
            continue
        m = re.match(r"\\(subsubsection|paragraph)\*?\{", s[i:])
        if m and m.group(1) in ("subsubsection", "paragraph"):
            j = match_brace(s, i + m.end() - 1)
            out.append("<alert>" + convert_inline(s[i + m.end():j], refs)
                       + ".</alert> ")
            i = j + 1
            continue
        m = re.match(r"\\(eqref|cref|Cref|ref|hyperref)(\[[^\]]*\])?\{([^}]*)\}", s[i:])
        if m:
            kind, opt, arg = m.group(1), m.group(2), m.group(3)
            if kind == "hyperref":
                # \hyperref[label]{text} -> xref with custom text dropped
                label = (opt or "[]")[1:-1]
                out.append(f'<xref ref="{refs.tag(label)}" text="global"/>')
            elif kind == "ref":
                # bare \ref = number only (the draft supplies its own type
                # word); PreTeXt's default xref text would duplicate it as
                # "Theorem Theorem 1.2" in every format
                parts = [a.strip() for a in arg.split(",")]
                out.append(", ".join(
                    f'<xref ref="{refs.tag(a)}" text="global"/>'
                    for a in parts))
            else:
                # \cref/\Cref/\eqref keep PreTeXt's default text form
                parts = [a.strip() for a in arg.split(",")]
                out.append(", ".join(f'<xref ref="{refs.tag(a)}"/>' for a in parts))
            i += m.end()
            continue
        m = re.match(r"\\cite(\[[^\]]*\])?\{([^}]*)\}", s[i:])
        if m:
            # PreTeXt renders a biblio xref as [n] already, and a pin belongs
            # in @detail ([n, pin]) — literal brackets here would double up.
            keys = [k.strip() for k in m.group(2).split(",")]
            pin = m.group(1)
            detail = ""
            if pin:
                pin_text = (pin[1:-1].replace("~", " ")
                            .replace("\\S", "\u00a7").replace('"', "'"))
                detail = f' detail="{xml_escape(pin_text)}"'
            parts = [f'<xref ref="bib-{tagify(k)}"'
                     + (detail if j == len(keys) - 1 else "") + "/>"
                     for j, k in enumerate(keys)]
            out.append(", ".join(parts))
            i += m.end()
            continue
        m = re.match(r"\\(emph|textit)\{", s[i:])
        if m:
            j = match_brace(s, i + m.end() - 1)
            out.append("<em>" + convert_inline(s[i + m.end():j], refs) + "</em>")
            i = j + 1
            continue
        m = re.match(r"\\textbf\{", s[i:])
        if m:
            j = match_brace(s, i + m.end() - 1)
            out.append("<alert>" + convert_inline(s[i + m.end():j], refs) + "</alert>")
            i = j + 1
            continue
        m = re.match(r"\\texttt\{", s[i:])
        if m:
            j = match_brace(s, i + m.end() - 1)
            inner = s[i + m.end():j].replace(r"\_", "_")
            out.append("<c>" + convert_inline(inner, refs) + "</c>")
            i = j + 1
            continue
        m = re.match(r"\\texorpdfstring\{", s[i:])
        if m:
            j = match_brace(s, i + m.end() - 1)
            inner = s[i + m.end():j]
            k = match_brace(s, j + 1) if j + 1 < n and s[j + 1] == "{" else j
            out.append(convert_inline(inner, refs))
            i = k + 1
            continue
        m = re.match(r"\\label\{([^}]*)\}", s[i:])
        if m:
            # stray label in prose: attach is context-dependent; drop + warn
            warn(f"stray \\label{{{m.group(1)}}} in prose dropped")
            i += m.end()
            continue
        m = re.match(r"\\(noindent|medskip|smallskip|bigskip|par|maketitle|"
                     r"tableofcontents|clearpage|newpage|allowbreak|indent)\b", s[i:])
        if m:
            i += m.end()
            continue
        m = re.match(r"\\(,|;|!|quad\b|qquad\b| )", s[i:])
        if m:
            out.append(" ")
            i += m.end()
            continue
        if s.startswith("``", i):
            out.append("<q>")
            i += 2
            continue
        if s.startswith("''", i):
            out.append("</q>")
            i += 2
            continue
        if s.startswith("---", i):
            out.append("<mdash/>")
            i += 3
            continue
        if s.startswith("--", i):
            out.append("<ndash/>")
            i += 2
            continue
        if c == "~":
            out.append("<nbsp/>")
            i += 1
            continue
        m = re.match(r"\\%", s[i:])
        if m:
            out.append("%")
            i += 2
            continue
        m = re.match(r"\\([&#$])", s[i:])
        if m:
            out.append(xml_escape(m.group(1)))
            i += 2
            continue
        m = re.match(r"\\([a-zA-Z]+)", s[i:])
        if m:
            ctxt = s[max(0, i - 40):i + 40].replace("\n", " ")
            warn(f"unhandled macro \\{m.group(1)} in prose (kept verbatim): ...{ctxt}...")
            out.append(xml_escape(m.group(0)))
            i += m.end()
            continue
        out.append(xml_escape(c))
        i += 1
    return "".join(out)


def match_brace(s: str, open_idx: int) -> int:
    """Given index of '{', return index of its matching '}'."""
    depth = 0
    for j in range(open_idx, len(s)):
        if s[j] == "{" and (j == 0 or s[j - 1] != "\\"):
            depth += 1
        elif s[j] == "}" and s[j - 1] != "\\":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("unbalanced braces")


class RefMap:
    """label -> tag, collecting labels first so forward refs resolve."""

    def __init__(self, labels: set[str]):
        self.labels = labels

    def tag(self, label: str) -> str:
        if label not in self.labels:
            warn(f"reference to unknown label '{label}'")
        return tagify(label)


# ---------------------------------------------------------------- block parser

@dataclass
class Ctx:
    refs: RefMap
    num: Numbering
    lean_map: dict = field(default_factory=dict)  # tag -> [{"decl": ...}, ...]
    lean_ann: dict = field(default_factory=dict)  # decl -> brief badge label
    out: list[str] = field(default_factory=list)
    indent: int = 0

    def emit(self, line: str) -> None:
        self.out.append("  " * self.indent + line)


BLOCK_RE = re.compile(
    r"\\(section|subsection)\*?\{"
    r"|\\appendix\b"
    r"|\\begin\{(" + "|".join(THEOREM_ENVS) + r"|proof|equation\*?|align\*?|"
    r"enumerate|itemize|center|verbatim|thebibliography|abstract|longtable|tabular)\}"
    r"|\\begin\{(equation|align)\}"
)


MATH_BLOCKS = {"equation", "equation*", "align", "align*"}


def parse_blocks(text: str, ctx: Ctx) -> None:
    """Convert a stretch of body text (inside document/section/theorem/proof).

    Display math joins the open paragraph (PreTeXt wants me/men/md inside <p>);
    paragraphs close at blank lines in prose and before non-math blocks.
    """
    pos = 0
    p_open = False

    def close_p():
        nonlocal p_open
        if p_open:
            ctx.indent -= 1
            ctx.emit("</p>")
            p_open = False

    def open_p():
        nonlocal p_open
        if not p_open:
            ctx.emit("<p>")
            ctx.indent += 1
            p_open = True

    while pos < len(text):
        m = BLOCK_RE.search(text, pos)
        upto = m.start() if m else len(text)
        chunk = text[pos:upto]
        paras = re.split(r"\n\s*\n", chunk)
        for k, para in enumerate(paras):
            if k > 0:
                close_p()
            if para.strip():
                open_p()
                ctx.emit(convert_inline(para.strip(), ctx.refs))
        # a trailing blank line before the block also closes the paragraph
        if re.search(r"\n\s*\n\s*$", chunk):
            close_p()
        if not m:
            break
        env = m.group(2) or m.group(3)
        if env in MATH_BLOCKS:
            open_p()   # display math lives inside the paragraph
        else:
            close_p()
        pos = dispatch_block(text, m, ctx)
    close_p()


def read_opt(text: str, pos: int) -> tuple[str | None, int]:
    if pos < len(text) and text[pos] == "[":
        j = text.index("]", pos)
        return text[pos + 1:j], j + 1
    return None, pos


def read_label(text: str, pos: int) -> tuple[str | None, int]:
    m = re.match(r"\s*\\label\{([^}]*)\}", text[pos:])
    if m:
        return m.group(1), pos + m.end()
    return None, pos


def dispatch_block(text: str, m: re.Match, ctx: Ctx) -> int:
    tok = m.group(0)
    if tok.startswith("\\appendix"):
        ctx.num.in_appendix = True
        ctx.num.section = ""  # next enter_section gives "A"
        return m.end()
    if m.group(1) in ("section", "subsection"):
        raise SectionBoundary(m.start())
    env = m.group(2) or m.group(3)
    body_start = m.end()
    end = find_env_end(text, body_start, env)
    # find_env_end matched \end{...}; body is up to its \end
    body_end = text.rindex("\\end{", body_start, end)
    body = text[body_start:body_end]

    if env in THEOREM_ENVS:
        convert_theoremlike(env, body, ctx)
    elif env == "proof":
        convert_proof(body, ctx)
    elif env in ("equation", "equation*"):
        convert_equation(body, env.endswith("*"), ctx)
    elif env in ("align", "align*"):
        convert_align(body, env.endswith("*"), ctx)
    elif env in ("enumerate", "itemize"):
        convert_list(env, body, ctx)
    elif env == "abstract":
        pass  # handled in frontmatter pass; skip here
    elif env == "verbatim":
        ctx.emit("<pre>")
        ctx.emit(xml_escape(body.strip("\n")))
        ctx.emit("</pre>")
    elif env == "center":
        parse_blocks(body, ctx)  # centering is presentational; recurse
    elif env in ("tabular", "longtable"):
        convert_tabular(env, body, ctx)
    elif env == "thebibliography":
        convert_bibliography(body, ctx)
    return end


class SectionBoundary(Exception):
    def __init__(self, pos: int):
        self.pos = pos


def convert_theoremlike(env: str, body: str, ctx: Ctx) -> None:
    title, p = read_opt(body, 0)
    label, p = read_label(body, p)
    number = ctx.num.next_thm()
    if label:
        tag = tagify(label)
    else:
        tag = f"thmlike-{number.replace('.', '-')}"
        warn(f"unlabeled {env} {number}: generated tag '{tag}' (drift hazard)")
    ctx.num.record(tag, env, label, number)
    set_block(tag)                      # ambiguous-notation decision grain
    ctx.emit(f'<{PTX_THM[env]} xml:id="{tag}">')
    ctx.indent += 1
    if title:
        ctx.emit(f"<title>{convert_inline(title, ctx.refs)}</title>")
    ctx.emit("<statement>")
    ctx.indent += 1
    parse_blocks(body[p:], ctx)
    ctx.indent -= 1
    ctx.emit("</statement>")
    # formalization badge(s): custom <lean> children, rendered by custom XSL
    # (block badge in HTML, dropped in the arXiv/latex conversion). Badge
    # text is "Lean", with a brief parenthetical to disambiguate when one
    # statement has several declarations; the full name stays in the tooltip.
    decls = ctx.lean_map.get(tag, [])
    for rec in decls:
        if len(decls) == 1:
            text = "Lean"
        else:
            ann = ctx.lean_ann.get(rec["decl"]) or rec["decl"].rsplit(".", 1)[-1]
            text = f"Lean ({ann})"
        ctx.emit(f'<lean ref="{rec["decl"]}">{text}</lean>')
    ctx.indent -= 1
    ctx.emit(f"</{PTX_THM[env]}>")
    set_block(_CURRENT_DIVISION[0])     # back to division grain


def convert_proof(body: str, ctx: Ctx) -> None:
    title, p = read_opt(body, 0)
    # attach to previous theorem: emitted as sibling; PreTeXt wants proof inside
    # the theorem element -- post-processing moves it (see reparent_proofs).
    ctx.emit("<proof>")
    ctx.indent += 1
    if title:
        ctx.emit(f"<title>{convert_inline(title, ctx.refs)}</title>")
    parse_blocks(body[p:], ctx)
    ctx.indent -= 1
    ctx.emit("</proof>")


def convert_equation(body: str, starred: bool, ctx: Ctx) -> None:
    label = None
    lm = LABEL_RE.search(body)
    if lm:
        label = lm.group(1)
        body = body[:lm.start()] + body[lm.end():]
    if starred:
        ctx.emit("<me>" + convert_math(body) + "</me>")
        return
    number = ctx.num.next_eq()
    tag = tagify(label) if label else f"eq-n{number.strip('()')}"
    if not label:
        warn(f"unlabeled equation {number}: generated tag '{tag}' (drift hazard)")
    ctx.num.record(tag, "equation", label, number)
    ctx.emit(f'<men xml:id="{tag}">' + convert_math(body) + "</men>")


def convert_align(body: str, starred: bool, ctx: Ctx) -> None:
    rows = split_rows(body)
    ctx.emit("<md>" if starred else "<mdn>")
    ctx.indent += 1
    for row in rows:
        row_label = None
        lm = LABEL_RE.search(row)
        if lm:
            row_label = lm.group(1)
            row = row[:lm.start()] + row[lm.end():]
        notag = bool(re.search(r"\\(notag|nonumber)\b", row))
        row = re.sub(r"\\(notag|nonumber)\b", "", row)
        attrs = ""
        if not starred:
            if notag:
                attrs = ' number="no"'
            else:
                number = ctx.num.next_eq()
                if row_label:
                    tag = tagify(row_label)
                else:
                    tag = f"eq-n{number.strip('()')}"
                ctx.num.record(tag, "align-row", row_label, number)
                attrs = f' xml:id="{tag}"'
        ctx.emit(f"<mrow{attrs}>" + convert_math(row) + "</mrow>")
    ctx.indent -= 1
    ctx.emit("</md>" if starred else "</mdn>")


def convert_list(env: str, body: str, ctx: Ctx) -> None:
    opt, p = read_opt(body, 0)  # drop enumitem options
    tag = "ol" if env == "enumerate" else "ul"
    items = re.split(r"\\item\b", body[p:])
    ctx.emit(f"<{tag}>")
    ctx.indent += 1
    for it in items:
        if not it.strip():
            continue
        it = re.sub(r"^\s*\[[^\]]*\]", "", it)  # per-item option
        ctx.emit("<li>")
        ctx.indent += 1
        parse_blocks(it, ctx)
        ctx.indent -= 1
        ctx.emit("</li>")
    ctx.indent -= 1
    ctx.emit(f"</{tag}>")


def convert_tabular(env: str, body: str, ctx: Ctx) -> None:
    ctx.emit("<!-- @forge: table auto-converted; verify formatting -->")
    body = re.sub(r"\\(toprule|midrule|bottomrule|hline|endhead|endfoot|"
                  r"endfirsthead|endlastfoot|centering)\b", "", body)
    body = body.strip()
    if body.startswith("{"):  # column spec (may contain nested braces)
        body = body[match_brace(body, 0) + 1:]
    ctx.emit("<tabular>")
    ctx.indent += 1
    for row in split_rows(body):
        if not row.strip():
            continue
        ctx.emit("<row>")
        ctx.indent += 1
        for cell in row.split("&"):
            ctx.emit("<cell>" + convert_inline(cell.strip(), ctx.refs) + "</cell>")
        ctx.indent -= 1
        ctx.emit("</row>")
    ctx.indent -= 1
    ctx.emit("</tabular>")


def convert_bibliography(body: str, ctx: Ctx) -> None:
    body = re.sub(r"^\{[^}]*\}", "", body.strip())
    items = re.split(r"\\bibitem\{([^}]*)\}", body)
    ctx.emit('<references xml:id="references">')
    ctx.indent += 1
    ctx.emit("<title>References</title>")
    for key, text_ in zip(items[1::2], items[2::2]):
        ctx.emit(f'<biblio type="raw" xml:id="bib-{tagify(key)}">')
        ctx.indent += 1
        ctx.emit(convert_inline(" ".join(text_.split()), ctx.refs))
        ctx.indent -= 1
        ctx.emit("</biblio>")
    ctx.indent -= 1
    ctx.emit("</references>")


# ------------------------------------------------------------- post-process

def reparent_proofs(lines: list[str]) -> list[str]:
    """Move a <proof> that immediately follows </theorem-like> inside it."""
    out: list[str] = []
    i = 0
    close_re = re.compile(r"^(\s*)</(" + "|".join(PTX_THM.values()) + r")>$")
    while i < len(lines):
        m = close_re.match(lines[i])
        nxt = i + 1
        if m and nxt < len(lines) and lines[nxt].strip() == "<proof>":
            # find matching </proof>
            depth = 0
            j = nxt
            while j < len(lines):
                if lines[j].strip() == "<proof>":
                    depth += 1
                elif lines[j].strip() == "</proof>":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            proof_block = lines[nxt:j + 1]
            out.extend("  " + ln for ln in proof_block)
            out.append(lines[i])
            i = j + 1
            continue
        out.append(lines[i])
        i += 1
    return out


# ------------------------------------------------------------------ driver

SEC_RE = re.compile(r"\\(section|subsection)\*?\{")


def parse_document(tex: str):
    """Split body into (heading, label, level, content) section units."""
    body = tex.split(r"\begin{document}", 1)[1].rsplit(r"\end{document}", 1)[0]
    units = []
    pos = 0
    pending_appendix = False
    matches = list(SEC_RE.finditer(body))
    preamble_chunk = body[:matches[0].start()] if matches else body
    for k, m in enumerate(matches):
        level = m.group(1)
        tstart = m.end()
        tend = match_brace(body, tstart - 1)
        title = body[tstart:tend]
        p = tend + 1
        label, p = read_label(body, p)
        end = matches[k + 1].start() if k + 1 < len(matches) else len(body)
        content = body[p:end]
        # \appendix sits between sections in the content of the previous unit
        units.append({"level": level, "title": title, "label": label,
                      "content": content})
    return preamble_chunk, units


def extract_macros(preamble: str) -> str:
    macros = []
    for m in re.finditer(r"\\newcommand\{\\[a-zA-Z]+\}(\[\d\])?\{", preamble):
        j = match_brace(preamble, m.end() - 1)
        full = preamble[m.start():j + 1]
        if "\\MarkedDem" in full or "hyperref" in full:
            continue  # structural macro, rewritten at parse time
        if _MATHBB_RE is not None:
            full = _MATHBB_RE.sub(r"\\mathbb{\2}", full)
        macros.append(full)
    return "\n".join(macros)


def extract_title_author(preamble: str):
    tm = re.search(r"\\title(\[[^\]]*\])?\{", preamble)
    title = ""
    if tm:
        j = match_brace(preamble, tm.end() - 1)
        title = preamble[tm.end():j]
        title = re.sub(r"\\texorpdfstring\{([^{}]*)\}\{[^{}]*\}", r"\1", title)
    am = re.search(r"\\author(\[[^\]]*\])?\{([^}]*)\}", preamble)
    author = am.group(2) if am else ""
    return title, author


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("texfile", type=Path)
    ap.add_argument("--out", type=Path, help="PreTeXt output dir (source/)")
    ap.add_argument("--numbering", type=Path, help="numbering JSON output")
    ap.add_argument("--snapshot", default="current", help="snapshot name for JSON metadata")
    ap.add_argument("--lean-annotations", type=Path,
                    help="optional {annotations: {decl: brief label}} sidecar "
                         "for disambiguating badges on multi-decl statements")
    ap.add_argument("--lean-map", type=Path,
                    help="tag -> decl-links JSON (from lean_declmap.py); "
                         "emits <lean> badges on matching statements")
    ap.add_argument("--notation-map", type=Path,
                    help="notation map JSON; wraps tracked notation in math "
                         "with \\notn{key}{...} at conversion time")
    ap.add_argument("--extra-biblio", type=Path,
                    help="biblio fragment file merged into <references>")
    ap.add_argument("--insertions", type=Path,
                    help="directory of anchored content fragments to merge")
    ap.add_argument("--disambig", type=Path,
                    help="block-grain sense decisions for ambiguous notation "
                         "(notation/disambiguation.json); unclassified "
                         "occurrences are reported, not wrapped")
    ap.add_argument("--author", action="append", default=[], dest="authors",
                    metavar="NAME|AFFIL_LINE|...",
                    help="additional author (repeatable); affiliation lines "
                         "separated by '|'. The special spec '@draft' "
                         "positions the draft's own author in the order; "
                         "without it the draft author comes first")
    ap.add_argument("--mathbb", metavar="LETTERS", default="",
                    help="restyle \\mathbf X -> \\mathbb{X} for these letters "
                         "(e.g. QZFP), in math and in docinfo macros")
    args = ap.parse_args()
    if args.notation_map:
        load_notation_wraps(args.notation_map, args.disambig)
    if args.mathbb:
        set_mathbb(args.mathbb)
    if args.extra_biblio and args.extra_biblio.exists():
        load_extra_biblio(args.extra_biblio)
    if args.insertions and args.insertions.exists():
        load_insertions(args.insertions)

    tex = strip_comments(args.texfile.read_text())
    # expand the one structural macro before parsing
    tex = tex.replace(r"\MarkedDem", r"\cref{prop:markedDem}")

    labels = set(LABEL_RE.findall(tex)) | set()
    refs = RefMap(labels)
    num = Numbering()
    lean_map = json.load(open(args.lean_map)) if args.lean_map else {}
    lean_ann = (json.load(open(args.lean_annotations)).get("annotations", {})
                if args.lean_annotations and args.lean_annotations.exists()
                else {})

    preamble = tex.split(r"\begin{document}")[0]
    title, author = extract_title_author(preamble)
    macros = extract_macros(preamble)
    pre_chunk, units = parse_document(tex)

    # abstract from the pre-section chunk
    am = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", pre_chunk, re.S)
    abstract_ptx = ""
    if am:
        actx = Ctx(refs, Numbering())  # abstract has no numbered items
        parse_blocks(am.group(1), actx)
        abstract_ptx = "\n".join(actx.out)

    sec_files = []
    for u in units:
        if u["level"] == "subsection":
            continue  # handled inside their section pass below
        pass

    # Re-walk: sections own their subsections (units list is flat)
    sections = []
    for u in units:
        if u["level"] == "section":
            sections.append({"title": u["title"], "label": u["label"],
                             "content": u["content"], "subs": [],
                             "appendix_before": False})
        else:
            sections[-1]["subs"].append(u)

    # \appendix appears in the content of the unit preceding the first appendix
    # section; detect from original text order.
    apx = tex.find("\\appendix")

    out_lines_per_sec = []
    for s in sections:
        # appendix switch if \appendix occurs before this section's heading
        spos = tex.find("\\section{" + s["title"])
        if spos == -1:
            spos = tex.find(s["title"])
        if apx != -1 and spos > apx and not num.in_appendix:
            num.in_appendix = True
            num.section = ""
        disp = num.enter_section()
        el = "appendix" if num.in_appendix else "section"
        tag = tagify(s["label"]) if s["label"] else "sec-" + slugify(s["title"])
        num.record(tag, el, s["label"], disp)
        set_division(tag)               # scoped notation wrapping
        ctx = Ctx(refs, num, lean_map, lean_ann)
        ctx.emit(f'<{el} xml:id="{tag}">')
        ctx.indent += 1
        ctx.emit(f"<title>{convert_inline(s['title'], refs)}</title>")
        wrap_intro = bool(s["subs"]) and s["content"].strip()
        if wrap_intro:
            ctx.emit("<introduction>")
            ctx.indent += 1
        try:
            parse_blocks(s["content"], ctx)
        except SectionBoundary:
            pass
        if wrap_intro:
            ctx.indent -= 1
            ctx.emit("</introduction>")
        for sub in s["subs"]:
            stag = tagify(sub["label"]) if sub["label"] else \
                tag + "-" + slugify(sub["title"])
            num.record(stag, "subsection", sub["label"], num.next_subsec())
            set_subdivision(stag)       # subsection-grain blocks, same scope
            ctx.emit(f'<subsection xml:id="{stag}">')
            ctx.indent += 1
            ctx.emit(f"<title>{convert_inline(sub['title'], refs)}</title>")
            parse_blocks(sub["content"], ctx)
            ctx.indent -= 1
            ctx.emit("</subsection>")
        ctx.indent -= 1
        ctx.emit(f"</{el}>")
        out_lines_per_sec.append((tag, el, reparent_proofs(ctx.out)))

    if args.out:
        title = convert_inline(title, refs)
        author = convert_inline(author, refs)
        write_tree(args.out, title, author, macros, abstract_ptx,
                   out_lines_per_sec, extra_authors=args.authors)
    if args.numbering:
        args.numbering.parent.mkdir(parents=True, exist_ok=True)
        args.numbering.write_text(json.dumps(
            {"snapshot": args.snapshot, "source": str(args.texfile),
             "items": num.records}, indent=1))
        print(f"wrote {args.numbering} ({len(num.records)} items)")
    if UNCLASSIFIED:
        n = sum(len(blocks) for blocks in UNCLASSIFIED.values())
        wl = (args.disambig.parent if args.disambig
              else args.notation_map.parent) / "unclassified.json"
        wl.write_text(json.dumps(UNCLASSIFIED, indent=1))
        warn(f"{n} ambiguous-notation blocks unclassified; worklist at {wl} "
             f"(occurrences left unwrapped)")
    print(f"{len(WARN)} warning(s)")
    return 0


HEADER = '<?xml version="1.0" encoding="utf-8"?>\n'


def extract_references(secs):
    """Pull a <references>...</references> block out of section line lists."""
    ref_lines = None
    for k, (tag, el, lines) in enumerate(secs):
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith("<references"):
                depth = 0
                for j in range(i, len(lines)):
                    if lines[j].lstrip().startswith("<references"):
                        depth += 1
                    if lines[j].strip() == "</references>":
                        depth -= 1
                        if depth == 0:
                            break
                ref_lines = lines[i:j + 1]
                secs[k] = (tag, el, lines[:i] + lines[j + 1:])
                return ref_lines
    return None


EXTRA_BIBLIO: list[str] = []       # <biblio> fragments merged into <references>
INSERTIONS: dict[str, list[tuple[str, str]]] = {}  # anchor tag -> [(pos, xml)]


def load_extra_biblio(path: Path) -> None:
    '''references/extra-biblio.xml: a fragment file whose <biblio> children are
    appended to the converted bibliography (process-1 additions that must
    survive re-ingestion).'''
    text = path.read_text()
    import re as _re
    EXTRA_BIBLIO.extend(m.group(0) for m in _re.finditer(
        r"<biblio\b.*?</biblio>", text, _re.S))


def load_insertions(d: Path) -> None:
    '''content/insertions/*.ptx: fragments with a first-line comment header
    <!-- anchor: TAG position: after|append --> merged at the anchor element.
    "after" places the fragment after the element's closing tag; "append"
    places it before the closing tag (inside, at the end).'''
    import re as _re
    for f in sorted(d.glob("*.ptx")):
        text = f.read_text()
        m = _re.search(r"<!--\s*anchor:\s*(\S+)\s+position:\s*(\w[\w-]*)\s*-->",
                       text)
        if not m:
            warn(f"insertion {f.name}: missing anchor header — skipped")
            continue
        body = text[m.end():].strip("\n")
        INSERTIONS.setdefault(m.group(1), []).append((m.group(2), body))


def apply_insertions(secs) -> int:
    '''Merge insertion fragments into the section line lists by anchor tag.'''
    n = 0
    for k, (tag, el, lines) in enumerate(secs):
        text = "\n".join(lines)
        for anchor, frags in INSERTIONS.items():
            marker = f'xml:id="{anchor}"'
            if marker not in text:
                continue
            for pos, body in frags:
                if pos == "after":
                    # after the anchor element's closing tag: find the element
                    # name, then its close following the marker
                    import re as _re
                    mm = _re.search(r"<(\w+)[^>]*" + _re.escape(marker), text)
                    if not mm:
                        continue
                    close = f"</{mm.group(1)}>"
                    i = text.find(close, mm.end())
                    if i >= 0:
                        j = i + len(close)
                        text = text[:j] + "\n" + body + text[j:]
                        n += 1
                elif pos == "prepend":
                    # inside the anchor element, right after its <title> (or
                    # after the opening tag when there is no title)
                    import re as _re
                    mm = _re.search(r"<(\w+)[^>]*" + _re.escape(marker) + r"[^>]*>",
                                    text)
                    if not mm:
                        continue
                    tclose = text.find("</title>", mm.end())
                    near = tclose >= 0 and tclose - mm.end() < 300
                    j = (tclose + len("</title>")) if near else mm.end()
                    text = text[:j] + "\n" + body + text[j:]
                    n += 1
                elif pos == "proof-append":
                    # inside the anchor element's LAST <proof>, at its end —
                    # for detail-tier elaborations of that proof
                    import re as _re
                    mm = _re.search(r"<(\w+)[^>]*" + _re.escape(marker), text)
                    if not mm:
                        continue
                    close = f"</{mm.group(1)}>"
                    i = text.find(close, mm.end())
                    p = text.rfind("</proof>", mm.end(), i) if i >= 0 else -1
                    if p >= 0:
                        text = text[:p] + body + "\n" + text[p:]
                        n += 1
                else:  # append (inside, at end)
                    import re as _re
                    mm = _re.search(r"<(\w+)[^>]*" + _re.escape(marker), text)
                    if not mm:
                        continue
                    close = f"</{mm.group(1)}>"
                    i = text.find(close, mm.end())
                    if i >= 0:
                        text = text[:i] + body + "\n" + text[i:]
                        n += 1
        secs[k] = (tag, el, text.split("\n"))
    return n


def write_tree(outdir: Path, title: str, author: str, macros: str,
               abstract: str, secs, extra_authors: list[str] = ()) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    napplied = apply_insertions(secs)
    if INSERTIONS and napplied < sum(len(v) for v in INSERTIONS.values()):
        warn(f"only {napplied} of {sum(len(v) for v in INSERTIONS.values())} "
             f"insertions found their anchor")
    refs_block = extract_references(secs)
    if refs_block and EXTRA_BIBLIO:
        closing = refs_block.pop()          # </references>
        refs_block.extend("      " + b for b in EXTRA_BIBLIO)
        refs_block.append(closing)
    main_incl = "\n".join(f'    <xi:include href="./{tag}.ptx"/>'
                          for tag, el, _ in secs if el == "section")
    apx_incl = "\n".join(f'      <xi:include href="./{tag}.ptx"/>'
                         for tag, el, _ in secs if el == "appendix")
    backmatter = ""
    if apx_incl or refs_block:
        refs_part = ("\n".join("      " + ln.strip() for ln in refs_block)
                     if refs_block else "")
        backmatter = f"""    <backmatter xml:id="backmatter">
{apx_incl}
{refs_part}
    </backmatter>"""
    def _xml_escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # --author specs in the order given; '@draft' places the draft's own
    # author (already inline-converted) explicitly, else it comes first
    draft_entry = f"        <author><personname>{author}</personname></author>"
    authors = []
    for spec in extra_authors:
        if spec.strip() == "@draft":
            authors.append(draft_entry)
            continue
        name, *aff = [p.strip() for p in spec.split("|")]
        if len(aff) == 1:
            inst = f"<institution>{_xml_escape(aff[0])}</institution>"
        elif aff:
            inst = ("<institution>"
                    + "".join(f"<line>{_xml_escape(l)}</line>" for l in aff)
                    + "</institution>")
        else:
            inst = ""
        authors.append(f"        <author><personname>{_xml_escape(name)}"
                       f"</personname>{inst}</author>")
    if draft_entry not in authors:
        authors.insert(0, draft_entry)
    authors_block = "\n".join(authors)

    main = f"""{HEADER}<pretext xml:lang="en-US" xmlns:xi="http://www.w3.org/2001/XInclude">
  <docinfo>
    <document-id>gq2-paper</document-id>
    <macros>
{macros}
\\newcommand{{\\notn}}[2]{{\\class{{ptxnotn-#1}}{{#2}}}}
\\newcommand{{\\notnfar}}[2]{{\\class{{ptxfar}}{{\\class{{ptxnotn-#1}}{{#2}}}}}}
    </macros>
  </docinfo>
  <article xml:id="paper">
    <title>{title}</title>
    <frontmatter>
      <titlepage>
{authors_block}
      </titlepage>
      <abstract>
{abstract}
      </abstract>
    </frontmatter>
{main_incl}
{backmatter}
  </article>
</pretext>
"""
    (outdir / "main.ptx").write_text(main)
    for tag, el, lines in secs:
        body = "\n".join(lines)
        (outdir / f"{tag}.ptx").write_text(HEADER + body + "\n")
    print(f"wrote {outdir}/main.ptx + {len(secs)} division files")


if __name__ == "__main__":
    raise SystemExit(main())

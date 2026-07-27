# Typst as an alternative backend

Status: **working spike**, on branch `typst-backend`. Everything described as
verified below was built and run; the gaps are listed honestly in
[What is not built](#what-is-not-built).

Built against **Typst 0.15.0**, whose HTML export sits behind
`--features html` and prints an "under active development" warning on every
run. Tracking issue: <https://github.com/typst/typst/issues/5512>.

## Verdict

Typst is a credible backend for the *interactive* half of paperforge, and it is
a **better fit than PreTeXt for detail tiers specifically** — the feature that
motivated looking at it.

It is **not** a drop-in replacement, for one structural reason and one large
practical one:

- **Typst cannot emit LaTeX.** The PreTeXt backend's whole reason for existing
  alongside the HTML is the arXiv-ready LaTeX target. Typst compiles to PDF
  directly and has no LaTeX writer, so an arXiv submission would have to go up
  as PDF-only. That is allowed but unusual for a mathematics paper, and it
  forecloses journal LaTeX workflows. This is the decision to make first;
  everything else is engineering.
- **`ingest/tex2ptx.py` is 1716 lines** of LaTeX→PreTeXt conversion (plus a
  numbering simulator validated 300/300 against pdflatex). A `tex2typ.py`
  sibling would reuse the parse and replace the emitter, but it is a real
  project, and there is no pandoc-style shortcut on this machine.

If the arXiv-LaTeX requirement stands, the honest framing is not
"Typst *instead of* PreTeXt" but **"Typst as a second HTML front end"**, or as
the backend for a future paper that does not owe anyone LaTeX.

## Why detail tiers are better here

This is the part worth the trouble. In the PreTeXt backend a tier needs **two
independent carriers**, because `@component` never reaches the HTML:

```xml
<p component="detail-2" detail-level="2">...</p>
```

— `@component` plus a publication `<version include="..."/>` excludes it from
the PDF at build time, and `@detail-level` on a born-hidden knowl drives the
HTML slider. Two mechanisms, kept in sync by hand.

In Typst one authored call serves both:

```typst
#detail(2)[The counting argument produces a surjection $Gamma arrow.twohead G$.]
```

```typst
#let detail(level, body, ..) = context {
  if target() == "html" {
    html.elem("details", attrs: ("data-detail-level": str(level)), ..)
  } else if level <= detail-level {          // detail-level = --input detail=N
    body
  }
}
```

- `typst compile paper.typ --input detail=1 out.pdf` — the block is not emitted.
- `typst compile paper.typ --input detail=3 out.pdf` — it is, inline, unmarked.
- HTML — always emitted, as `<details data-detail-level="2">`; `paper.js`
  opens or collapses it from one slider.

**Verified on the example and on real gq2 content.** Extracting text from the
three PDFs of `typst-template/example`:

| authored block | `--input detail=1` | `detail=2` | `detail=3` | HTML |
|---|---|---|---|---|
| `#detail(2)[...]` | absent | present | present | collapsed, openable |
| `#detail(3)[...]` | absent | absent | present | collapsed, openable |
| `#detail-inline(2)[...]` | absent | present | present | hidden, revealable |

The HTML is built **once** and carries every tier; only the PDFs are built per
tier, because a PDF cannot change its mind.

There is also `#detail-upto(n)[...]` for the complement — a one-line summary
that a reader who has expanded the full argument no longer needs.

## What Typst 0.15's HTML export actually does

Probed directly rather than taken from the tracking issue.

| capability | result |
|---|---|
| **Math** | **Native MathML.** `<msub>`, `<mfrac>`, `<munder>`, … plus a bundled `<style>` block for alignment/accent polish. **No MathJax, no KaTeX, no typesetting JS at all.** |
| `target()` | works — the conditional that makes one source serve both outputs |
| `html.elem(tag, attrs:, body)` | works, with arbitrary tags and `data-` attributes |
| Cross-references | `<a href="#tag">Section 2</a>`, with correct numbering |
| Citations | `<a role="doc-biblioref">[1, Thm. 8.1.2]</a>` — pinned citations included |
| Bibliography | `<section role="doc-bibliography">` with backlinks |
| Footnotes | `role="doc-noteref"` / `role="doc-endnotes"` |
| Figures, tables | `<figure>`, `<figcaption>`, `<thead>`/`<tbody>` |
| Outline | `outline()` emits a real `<nav role="doc-toc">` — the book sidebar |
| `sys.inputs` | `--input k=v`, the PDF-side detail knob |
| `html.frame(..)` | embeds paged content as self-contained SVG (fonts inlined) — the escape hatch for anything HTML cannot express, e.g. commutative diagrams |

Math coverage is the pleasant surprise. A battery of what a number-theory paper
actually uses — accents, `bb`/`cal`/`frak`, matrices, cases, big operators,
stretched and squiggly arrows, fractions, roots, binomials, `attach`,
`underbrace`, `limits(lim)_(<--)` — exported with exactly **one** failure:

```
warning: overline was ignored during MathML export
```

`lib/mathcompat.typ` shims it as `overbar`, routing to `math.macron` (which
exports a correct `<mover>`) in HTML and the built-in `overline` in the PDF.

## Gaps that needed a workaround

| gap | workaround | where |
|---|---|---|
| Block equations get no visible number in HTML (the *reference* resolves, the equation shows nothing) | show rule wrapping `<math display="block">` in a grid with the number in the margin | `lib/paperforge.typ` |
| No way to write into the real `<head>`; an `html.elem("head")` lands at the top of `<body>` | park tags in `<template id="pf-head-assets">`, lift them after the build | `scripts/postprocess.py` |
| Typst emits `id` only for elements something references, but paperforge needs a stable id on **every** statement (deep links, margin review, click-to-mark) | set `id` from the label in the statement show rule — verified not to collide with Typst's own | `lib/theorems.typ` |
| Equation references render "Equation 4", not the `\eqref` convention | show rule on `ref` to `math.equation` → `(4)`, so ranges read `(4)–(6)` | `lib/paperforge.typ` |
| No AMS citation style bundled | default numeric matches what PreTeXt already produces; a real switch ships an AMS CSL file | instance |
| `.bib` fields pass most LaTeX math through verbatim — `{$\mathfrak{p}$}` renders as the literal string `\mathfrak{p}` | use the Unicode character (`𝔭`) in the `.bib` | instance |
| Multi-page output (`--format bundle`) is experimental and wants a `document` wrapper not present in 0.15's `html` module | not needed — the gq2 HTML is deliberately a single page (PreTeXt chunking level 0) | — |

## Traps worth knowing

Each of these cost real time and none of them announce themselves.

1. **`display: block` on a `<math>` element destroys MathML layout.** MathML
   Core gives it `display: block math`; dropping the `math` keyword makes every
   child its own block, so a one-line equation renders as a vertical stack of
   symbols. Set only the margin.
2. **A Typst import list does not continue across a line break.** A wrapped
   `#import "x.typ": a, b,\n c, d` silently imports only the first line's names,
   and the rest fail later as "unknown variable". Use `*`.
3. **Hyphens are subtraction in math mode.** `overline-c(QQ)` parses as
   `overline - c(QQ)` and renders as literal text. Macro names used inside
   `$..$` must be hyphen-free.
4. **A notation marker inside `$..$` and one in prose are different elements.**
   `<mrow>` is valid only within `<math>`; used in prose, Typst drops what it
   cannot express — "accent was ignored", "attach was ignored" — so `Ẑ` exports
   as a bare `Z`. Hence `notn` (in math) *and* `notn-inline` (in prose).
5. **CSS `attr()` reads the attribute of its own element**, so a
   `.pf-detail > summary::after { content: attr(data-level) }` reading a
   `data-level` on the `<details>` renders empty. `paper.js` mirrors the tier
   onto the `<summary>`.
6. **A reference into a detail block breaks the lower-detail PDF build**
   ("label `<eq-boundary>` does not exist"). This is correct behaviour, and in
   the same spirit as the rest of paperforge — a checkable handle failing loudly
   rather than rotting silently — but it is an authoring invariant that wants a
   validator: *no reference may target content tiered above its own level.*
7. Dictionary keys must be strings (`"1": ..`, not `1: ..`).
8. Renamed symbols: `angle.l`/`angle.r` → `chevron.l`/`chevron.r`; `∂` is
   `partial`, not `diff`.
9. A detail preference in `localStorage` is shared across papers and must be
   clamped to the current document's maximum tier, or the slider reads "3 / 2".

## Verified on real content

`gq2-paper` branch `typst-backend`, directory `typst/`: section 1 of the actual
paper — prose verbatim from `inputs/draft/gq2-paper.tex`, the marked-Demushkin
proposition, the presentation theorem, ten numbered equations, the auxiliary
word displays, pinned citations.

It builds to HTML plus three PDFs with **zero warnings**, and:

- statements share one counter (Proposition 1.1, Theorem 1.2) and references
  resolve at the *target's* location;
- the presentation theorem carries **two** formalization badges in different
  colours — `gq2-claude` green, `gq2-gpt` indigo — from
  `lean: (("GQ2.Presentation.main", "gq2-claude"), ("Q2Presentation.thm_main", "gq2-gpt"))`;
- `⟨a, s, y | a²s⁴[s,y] = 1⟩_pro-2` and the word displays render correctly in
  MathML;
- the three tiered passages are absent from the `detail=1` PDF (3628 chars) and
  present in `detail=2` (4862 chars), while the HTML carries all of them.

## How much of the paper this actually covers

Small, and deliberately so — the spike is a **rendering test**, not a
conversion. It took the passage with the paper's hardest notation to find out
whether Typst could express the mathematics at all.

| | gq2 draft | converted |
|---|---|---|
| lines | 6178 | 113 |
| statements | 105 | 2 |
| proofs | 86 | **0** |
| sections | 13 + appendices | part of §1 |

To size the rest without converting it, the draft was surveyed for the
constructs a converter would meet:

- **Nothing to fear graphically.** Zero `tikz`, `xymatrix`, `CD` and zero
  `includegraphics` — no commutative diagrams, so `html.frame` is never needed.
- **Exports correctly** (spot-checked directly): `align` (as
  `<mtable class="multiline-equation aligned">`), `cases`, matrices, `array`,
  stretched arrows (`arrow.r^f`).
- **Two further gaps found**, on top of `overline`:

  1. **`substack` (5 uses).** Typst's `stack()` is *ignored during HTML export* —
     a sum silently loses its limits. The working idiom is a linebreak inside
     the subscript, `sum_(i < n \ j > 0)`, which exports as a proper
     `<munder>` with a stacked `<mtable>`.
  2. **A multi-line display is ONE numbered equation in Typst**, not one number
     per line as in LaTeX `align`. Of 25 `align`/`split`/`gather` blocks
     (7 unnumbered), **11 carry more than one `\label`** and would have to be
     split into separate displays — e.g. `eq:D0`/`eq:D1`/`eq:D2`,
     `eq:shapirosquare`/`eq:shapirofree`/`eq:shapiroevens`. Bounded work, but a
     converter has to know to do it.

The 86 unconverted proofs are the largest untested surface, and the appendices
(normalized cochains, Fox–Heisenberg rules, the square-commutator presentation)
carry the densest displays in the paper.

## What is not built

Listed so nobody mistakes the spike for a backend.

- **`tex2typ.py`** — the LaTeX→Typst converter. The gq2 section was converted by
  hand. This is the largest single item.
- **arXiv LaTeX** — impossible, not merely unbuilt. See the verdict.
- **Validators** — all eight read PreTeXt via `validators/_document.py`. Under
  Typst they would need a source reader; several (`notation_order`,
  `lean_links`, `references`) are otherwise format-agnostic in spirit.
- **The review server and paper-view editor** — margin markers, click-to-mark
  and lane-1 editing all address PreTeXt ids and draft byte-spans.
- **Knowls** — PreTeXt's click-to-preview cross-references have no analogue
  here; they would be JS over the existing anchors.
- **`blueprint_gen.py` / `lean_knowls.py` / `trust_table.py`** — these read the
  Lean side and emit PreTeXt; they would need Typst emitters.
- **The numbering simulator and drift validator** (requirement 13) — Typst
  numbers documents itself, so the simulator's job changes shape entirely;
  `typst query` could probably replace it, which would be a simplification.

## Running it

```bash
# once: make the backend importable as @local/paperforge:0.1.0
typst-template/scripts/install-local-package.sh

# the example: HTML + one PDF per tier
typst-template/scripts/build.sh typst-template/example/paper.typ output 1 2 3

# the gq2 spike (from the gq2-paper checkout, branch typst-backend)
PAPERFORGE=/path/to/paperforge typst/scripts/build.sh
```

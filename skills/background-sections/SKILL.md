---
name: background-sections
description: Write collapsed background material — a Background section after the introduction for paper-wide prerequisites, and per-section background blocks for locally-used material — summarizing exactly what is needed to read the paper.
---

# background-sections

Research papers assume background their actual readers may not have. This
skill adds it *without lengthening the paper*: background renders like
proofs — collapsed knowls, expanded on click — and is excluded from the
default PDF via detail-level machinery.

## Structure

- **Paper-wide background** — a `Background` section after the introduction:
  material used throughout (for gq2: profinite presentations and counting,
  Demushkin groups, local class field theory conventions, group cohomology
  and duality at the level the paper uses them).
- **Per-section background** — a collapsed block at the start of a section,
  for material used only there (e.g. Arf invariants and quadratic forms in
  characteristic 2 before the quadratic-layer section; Fox calculus before
  the deformation section).

Each block answers: *what does the reader need to know to follow THIS
paper's use of the notion* — not a survey. Cite the standard sources (the
bibliography already carries them: NSW, Serre, Labute, O'Meara, …) and defer
to them for proofs. Where a background notion has a formalized counterpart,
link it (`<lean>`).

## Selection (author-driven)

The author supplies the topic list — do not guess what the audience is
missing. Seed sources for proposals: the notation map's imported concepts,
the citation-needs `common-knowledge` decisions (things deemed too standard
to cite are exactly background candidates), and the axiom census (each
foundational input names a theory the reader must trust).

## Mechanics

- Paper-wide section: a new source fragment merged as an insertion after the
  introduction (`position: after`, anchor = the introduction section), as a
  `<section>` whose subsections carry `detail-level` attributes → collapsed.
- Per-section blocks: insertions with `position: prepend` on the section,
  `<remark detail-level="1"><title>Background: …</title>` (or a dedicated
  title convention), rendering as a collapsed knowl at the section top.
- Background prose is generated content: style-corpus matched,
  plagiarism-checked, author-reviewed like everything else.

## Contract

- **Reads:** the author's topic list (directives or chat); the bibliography
  + local PDFs for the deferred-to sources; `style.corpus`/`style.advice`.
- **Writes:** insertion fragments in `content/insertions/` (one per
  background block).
- **Gate:** `plagiarism.py` (background prose is the highest-risk content
  for accidental source echoing — check against the very sources it
  summarizes); `references.py` (citations resolve); `run_all`.
- **Provenance:** fragment header names the generator; commits carry
  `Generated-by: <model-id>`.

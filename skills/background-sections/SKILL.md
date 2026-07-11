---
name: background-sections
description: Write collapsed background material — a Background section after the introduction for paper-wide prerequisites, and per-section background subsections for locally-used material — drafted ONLY from author-supplied references, summarizing exactly what is needed to read the paper.
---

# background-sections

Research papers assume background their actual readers may not have. This
skill adds it *without lengthening the paper*: background renders like
proofs — collapsed knowls, expanded on click — and is excluded from the
default PDF via detail-level machinery. Readers expand only what they
don't already know.

## Structure

- **Paper-wide background** — a `Background` section immediately after the
  introduction: material used in multiple sections, or needed to understand
  the statements of the main results (for gq2: profinite presentations and
  counting, Demushkin groups, local class field theory conventions, group
  cohomology and duality at the level the paper uses them).
- **Per-section background** — a background subsection at the *beginning*
  of a section, for material needed only in that section (e.g. Arf
  invariants and quadratic forms in characteristic 2 before the
  quadratic-layer section; Fox calculus before the deformation section).

Each block answers: *what does the reader need to know to follow THIS
paper's use of the notion* — not a survey. Defer to the sources for proofs.
Where a background notion has a formalized counterpart, link it (`<lean>`).

## Selection (author-driven, via marks)

The worklist is the author's **background marks**: `directives/marks.json`
entries with `mode: "background"`, placed with the 📖 pen while reading
(click or phrase-selection). Each mark carries the clicked/selected text,
its context sentence, and the anchor block — enough to decide the topic and
whether it is paper-wide (used in several sections / main-result
statements) or section-local. Do not guess topics the author has not
marked; propose candidates at most (seeds: the notation map's imported
concepts, `common-knowledge` citation decisions, the axiom census).

Group marks into topics before drafting: several marks about quadratic
forms are ONE background block. Record the grouping in the fragment header
comment (mark ids), and flip the consumed marks to `applied` with a note.

## Plagiarism guardrail (hard requirement)

Background prose is the highest-risk content for source echoing, so:

1. **The author must supply the references.** Required reading for a topic
   must exist as PDFs (or source) under `references/` before drafting.
   If a topic's natural source is missing, STOP and ask the author to
   download it — do not draft from memory.
2. **Draft only from the provided references.** Every generative prompt for
   a background block must state explicitly: *use only the attached
   reference excerpts; do not rely on prior knowledge of the material; if
   the excerpts do not cover something, say so instead of filling in.*
3. **Link to the specific part of the reference** that each background
   block summarizes — a `<xref detail="…"/>` pin (chapter/section/theorem
   number), not a bare citation.
4. Run the plagiarism validator against exactly the sources summarized;
   background blocks must clear it like all other pipeline-added prose.

## Terminology links (coupling with the notation system)

Background blocks are the *targets* of terminology links: phrases the
author marks with the terminology pen (`mode: "terminology"`) get a hover
with a short summary and a "more details" link pointing at the background
block that reviews the notion. When drafting a block, check for open
terminology marks about it, and give the block a stable `xml:id`
(`bg-<topic>`) so the terminology registry can anchor to it.

## Mechanics

- Paper-wide section: a new source fragment merged as an insertion after
  the introduction section (`position: after`, anchor = the introduction
  section), as a `<section xml:id="sec-background">` whose subsections
  (`xml:id="bg-<topic>"`) carry `detail-level` attributes → collapsed.
- Per-section blocks: insertions with `position: prepend` on the section
  (they land inside an existing `<introduction>` automatically), as
  `<remark detail-level="1"><title>Background: …</title>` or a
  `bg-<topic>`-id'd collapsed block at the section top.
- Background prose is generated content: style-corpus matched,
  plagiarism-checked, author-reviewed like everything else.

## Contract

- **Reads:** `directives/marks.json` (`mode: "background"`, status open);
  author-supplied PDFs under `references/`; the bibliography;
  `style.corpus`/`style.advice`; open `terminology` marks (for target ids).
- **Writes:** insertion fragments in `content/insertions/` (one per
  background block, header lists consumed mark ids); mark status flips to
  `applied`.
- **Gate:** `plagiarism.py` against the summarized sources (hard);
  `references.py` (pins resolve); `run_all`.
- **Provenance:** fragment header names the generator; commits carry
  `Generated-by: <model-id>`.

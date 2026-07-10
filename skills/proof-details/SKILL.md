---
name: proof-details
description: Write higher-detail-level elaboration blocks inside proofs, using the formal (Lean) proof as the guide for what deserves explanation; surfaced by the proof-local ">details" button.
---

# proof-details

The paper's proofs are written at the default detail level. This skill adds
`detail-level="N"` blocks *inside* proofs — collapsed by default, revealed by
the proof-local "▸ details" button (detail-ui.js) or the global slider — so a
reader can step into a proof without the paper growing.

## What makes a good detail block (the Lean proof is the guide)

- **Explain what the formal proof revealed**: hypotheses the paper elides but
  the formalization needed (and why they are harmless in context), case splits
  the prose compresses, where finiteness/compactness actually enters. This is
  material no referee gets from the prose alone.
- **Unpack the step a reader would check by hand**: the one computation or
  diagram chase the prose waves at.
- Do not restate the proof at the same level, and never transcribe Lean —
  translate what its structure *teaches* into mathematics.
- 1–2 paragraphs per block; a proof can carry blocks at several levels
  (level 2 = elaboration, level 3 = full detail) — deeper levels nest more.

## Mechanics

- Locate the Lean proof via the crosswalk (`crosswalk/lean-decl-map.json` →
  decl, file, line) and read it before writing anything.
- Output = one insertion fragment per proof in `content/insertions/`
  (header: `<!-- anchor: <tag> position: proof-append -->`), containing
  `<remark detail-level="2" component="details" xml:id="det-<tag>">
  <title>More detail</title>…`. Merged at ingest by `tex2ptx --insertions`.
  The `component` attribute is what excludes the block from the PDF (the
  arxiv/print publication files use `<version include=""/>`); the
  `detail-level` attribute is what the HTML slider and the proof-local
  button key on. Both are required.
- Pilot exemplar: `40-proof-details-pilot.ptx` in the gq2 instance
  (lem-reconstruction).

## Contract

- **Reads:** the paper's proofs; the Lean proofs via the crosswalk;
  `style.corpus`/`style.advice`.
- **Writes:** insertion fragments (`content/insertions/*-details-*.ptx`),
  one per proof, `detail-level` ≥ 2.
- **Gate:** `pretext build web` (fragment merges cleanly); `plagiarism.py`
  on the new prose; `run_all` stays clean. The author reviews blocks in the
  diff / on the page.
- **Provenance:** fragment header comment names the generator; commits carry
  `Generated-by: <model-id>`.

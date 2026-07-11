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
- Scatter detail paragraphs through the proof: each paragraph should follow
  the authored paragraph whose step it elaborates. Do not collect independent
  explanations into an appendix-like block at the end of the proof.
- 1–2 paragraphs per proof; a proof can carry blocks at several levels
  (level 2 = elaboration, level 3 = full detail) — deeper levels nest more.

## Mechanics

- Locate the Lean proof via the crosswalk (`crosswalk/lean-decl-map.json` →
  decl, file, line) and read it before writing anything.
- Output = one insertion fragment per proof in `content/insertions/`.
  Precede each detail paragraph with
  `<!-- anchor: <tag> position: proof-after-N -->`, where `N` is the 1-based
  number of the authored proof paragraph it elaborates. A single fragment may
  contain several such placements. Use `proof-append` only when a detail
  genuinely elaborates the proof's final conclusion rather than an earlier
  step.
- Each placement contains a bare
  `<p detail-level="2" component="details">…</p>` paragraph — no remark
  wrapper, title, or number. It should read as a natural continuation
  ("In more detail: …" where useful). Merged at ingest by
  `tex2ptx --insertions`.
  The `component` attribute excludes the paragraph from the PDF (the
  arxiv/print publication files use `<version include=""/>`); the
  `detail-level` attribute is what the HTML slider and the proof-local
  "▸ details" button key on. Both are required.
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

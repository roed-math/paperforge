---
name: citation-audit
description: Classify facts that may need citations (background theory, named theorems, prior definitions) and route fixes; the deterministic axiom-coverage check is the references validator's job. Process 2 of docs/REFERENCES.md.
---

# citation-audit

The LLM half of citation completeness. The validator already gates the
formalization's axioms; this skill covers what no extractor can list: prose
that *recalls known mathematics* without citing it.

## Worklist construction (deterministic first)

Scan the assembled document for citation-suspect blocks:
- named results: capitalized surname within 4 words of theorem / lemma /
  classification / duality / formula / criterion ("Labute's classification",
  "local Tate duality", "Schur–Zassenhaus");
- appeal-to-authority phrases: "well known", "classical", "standard",
  "it is known", "one knows", "by the theory of";
- `<lean>`-badged statements whose Lean docstring cites literature the
  paper-side block does not.

## Classification (block-grain, cached)

For each suspect block decide: `needs-citation` (naming the work) |
`cited-nearby` (a citation within the same division suffices) |
`common-knowledge` (no citation expected at this paper's level). Decisions go
in `references/citation-needs.json` — committed, reviewable, incremental
under draft updates (same pattern as notation/disambiguation.json).

## Fixes

`needs-citation` decisions become: an existing-entry citation inserted via a
content insertion, or (new work) a literature-connections addition, or a
directive when placement/wording needs the author. Never silently edit.

## Locator pins

A citation that supports a specific claim carries a **locator** — the
theorem/section/page inside the work ("[JS, Theorem 3.4]", "[NSW,
(7.2.6)]"), not a bare "[JS]". The gq2 release-eve pass (2026-07-27)
audited all 325 citation occurrences this way. Rules:

- **Verify against the source PDF before editing.** A pin is added or
  changed only after the cited statement is located in the actual source
  (the PDFs under `references/`); page offsets of scans are noted. A pin
  that cannot be verified becomes a directive for the author, not a guess.
- Prefer the source's own numbering (the theorem heading in the author
  PDF), and pin translations/reprints to the edition the bibliography cites.
- Record the audit in `references/PROVENANCE.md`: which pins were verified,
  against which file, and any source mismatches found (a wrong-paper
  citation is a bibliography fix, not just a pin fix).

## Calibration

The bar is "what a careful referee flags", not "cite everything": a paper on
G_Q2 does not cite a textbook for Sylow's theorem. When unsure, prefer
`needs-citation` with a note — the author reviews the decisions file.

## Contract

- **Reads:** the assembled document; Lean docstring citations; the existing
  `references/citation-needs.json` (incremental — reviewed decisions are
  immutable).
- **Writes:** new decision items in `citation-needs.json`; fixes as insertions
  or directives (never silent edits).
- **Gate:** `run_all` references checks; the author reviews decisions in the
  dashboard.
- **Provenance:** every proposed item carries `"generator": "<model-id>"`;
  re-runs never modify `status`/`author_note` on existing items.

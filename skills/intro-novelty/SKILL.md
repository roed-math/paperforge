---
name: intro-novelty
description: Add language to the introduction articulating what parts of the proof are interesting or novel, grounded in what is actually proved.
---

# intro-novelty

Requirement 7. The AI draft rarely says *why the work matters*; this adds it.

## Behavior
- Read the whole document first, plus `style.advice`, to identify genuinely novel
  or interesting steps (a new lemma, an unexpected reduction, a technique reused in
  a new setting).
- Draft intro prose that names these explicitly and points forward to where they
  appear (cross-referencing the relevant `xml:id`s).
- Where a claim of novelty is a value judgment, surface it to the author for
  confirmation via a `<!-- @forge: novelty claim — confirm? -->` marker rather than
  asserting it unilaterally.

## Guardrails
- Do not overclaim. Novelty statements that the paper does not support are a
  correctness/credibility risk, not just a style issue.
- Generated prose → plagiarism-checked; match the author's corpus.

# Plagiarism guard

The concern: Claude reuses language from the AI draft or the cited sources in a way
that exposes the author to a plagiarism accusation. This is the one requirement
where "the model tried to be careful" is not auditable enough, so it is handled by
a **deterministic validator plus human review**, not a generation prompt.

## What the validator does (`validators/plagiarism.py`)

- Builds an n-gram index (default 7-word shingles, configurable) over the
  **sources**: the AI draft and every PDF in `references/`.
- Scans the generated PreTeXt prose (excluding math, `verbatim` directives, and
  quoted+attributed passages) for shingles that overlap a source.
- Reports each overlapping span with its location (`xml:id`) and the source it
  matches, ranked by length. It does **not** edit anything.

## What is exempt

- **Math** — notation and formulas are not prose and are not flagged.
- **`verbatim` directives** — your own words (see [DIRECTIVES.md](DIRECTIVES.md)).
- **Explicit quotes** — a passage wrapped in PreTeXt `<q>`/`<blockquote>` with a
  citation is allowed (that is correct scholarly practice, not plagiarism).

## Two-stage review (mirrors the reference check)

1. **Automated** — the validator flags overlaps; the author rewrites flagged spans
   (or converts them to attributed quotes) until the report is clean.
2. **Manual** — the author does a final human read. The validator reduces the
   surface to review; it does not replace judgment.

## Why this shape

- Overlap with *sources* is the objective, checkable proxy for the risk.
- Generated text is *always* checked; author text is *never* falsely flagged —
  because the `verbatim`/`instruct` split tells them apart.
- Every accepted insertion is a git commit (see DIRECTIVES.md), so if a question
  ever arises, the origin of any sentence is recoverable.

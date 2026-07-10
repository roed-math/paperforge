---
name: intro-novelty
description: Write the introduction's novelty exposition FROM the approved claims of the novelty dossier (novelty/claims.json) — never from scratch. Requirement 7; see docs/NOVELTY.md.
---

# intro-novelty

The novelty paragraphs are the part of an introduction LLM-generated text most
often gets wrong, because they require literature knowledge. This skill
therefore does NOT invent novelty statements: it renders the **dossier**.

## Pipeline position

1. `ingest/novelty_evidence.py` collects deterministic seeds (novel-node
   inventory, definition genericity + fan-in, contrast language, census
   events, Mathlib import profile, method units).
2. An LLM pass drafts typed claims (the five classes: novel method /
   surprising result / weakened hypotheses / generalizable definition /
   cross-field ingredient), verifies each against the local reference PDFs
   and targeted web searches, and records the search trail — including
   demotions (a "novel method" that turns out classical becomes an
   ingredient claim, with the discovery recorded).
3. **The author reviews the dossier** — via the review dashboard
   (docs/REVIEW.md; `review/review_server.py`) or in chat — flipping statuses to
   `author-approved` / `author-rejected`, edits statements, adds context.
4. THIS skill writes prose from `author-approved` claims only.

## Rendering rules (statements are markup, not raw material)

- Claim statements arrive as inline LaTeX (docs/NOVELTY.md). Convert each
  deterministically:  `python3 <paperforge>/ingest/claim_inline.py` (stdin
  LaTeX -> stdout PreTeXt inline; it reuses tex2ptx.convert_inline, so
  \cite becomes the same `[<xref ref="bib-KEY"/>, pin]` form as the paper's
  own citations). Do NOT hand-translate or paraphrase.
- Before rendering a claim with `new_refs`, materialize those entries into
  `references/extra-biblio.xml` via `claim_inline.py --biblio '<latex>'
  --key bib-KEY`. Every \cite key must resolve afterward — the references
  validator's dangling-cite check is the gate.

## Writing rules

- One paragraph group per theme, not per claim; merge claims that tell one
  story (e.g. class-2 obstruction + class-5 toolkit = "why p=2 is different
  and what it costs").
- Keep the dossier's hedges: "to our knowledge", "we found no earlier
  instance" — never strengthen a hedge the evidence doesn't support.
- Cite the works named in each claim's evidence; the citations must resolve
  (references validator).
- Weakened-hypothesis claims (class 3) may point at the Lean statement — the
  machine-checkable form is itself worth a sentence.
- Traceability: emit an XML comment before each paragraph listing the claim
  ids it renders, so drift between dossier and prose is diffable.
- Output goes through `content/insertions/` (survives re-ingestion), anchored
  in the introduction; plagiarism-checked like all generated prose.

## Guardrails

- `proposed` and `needs-discussion` claims are invisible to this skill.
- If the introduction already contains novelty statements not backed by any
  approved claim, flag them to the author rather than silently keeping or
  deleting them.

## Contract

- **Reads:** `novelty/claims.json` — `author-approved` claims ONLY;
  `references/extra-biblio.xml` for `new_refs` resolution.
- **Writes:** intro fragments in `content/insertions/` (with claim-id XML
  comments for traceability); new bib entries via `claim_inline.py --biblio`.
- **Gate:** `references.py` (no dangling or unused entries) + `plagiarism.py` +
  full `run_all`.
- **Provenance:** `Generated-by: <model-id>` trailer on the commits; each
  paragraph's claim-id comment ties prose back to dossier items, whose own
  `generator` field names their proposer.

---
name: literature-connections
description: Find literature the paper should acknowledge (prior work, applications, context), draft citing prose for the introduction, and add the bibliography entries. Process 1 of docs/REFERENCES.md.
---

# literature-connections

Adds *outbound* references — work the proof does not depend on but the paper
should situate itself against. Every addition is a pair: bib entry + citing
prose (the unused-entry validator rejects orphans).

## Candidate mining (strongest signal first)

1. The formalization's citation discipline: `docs/literature-axioms.md` in the
   Lean repo and docstring `Citation:` lines — works already load-bearing.
2. The draft's prose: named results/people mentioned without bib entries.
3. Web + arXiv search on the paper's subjects and the obvious adjacent
   questions (for gq2: prior presentations of local absolute Galois groups —
   Jannsen–Wingberg, Zel'venskii's dyadic pro-2 work, Diekert; Demushkin
   theory — Labute, Serre; applications of explicit presentations —
   deformation-theoretic and computational).

## Judgment per candidate

Classify: prior-work | method | application | context. Ask: would a referee
or the cited author reasonably expect this citation? If unsure, queue it as a
question for the author rather than deciding.

## Output (both must survive re-ingestion)

- Bib entry appended to `references/extra-biblio.xml` (PreTeXt `<biblio
  type="raw" xml:id="bib-...">`), merged by `tex2ptx --extra-biblio`.
- 1–3 sentences of intro prose as a fragment in `content/insertions/`
  (header: `<!-- anchor: sec-introduction-... position: append -->`), merged
  by `tex2ptx --insertions`. Anything carrying a novelty/priority claim goes
  through a directive for author approval instead of direct insertion.

## Guardrails

- Generated prose is plagiarism-checked like everything else; match the style
  corpus.
- Never fabricate a reference: every entry must correspond to a real work you
  located (record where you found it in the commit message).
- Prior-work claims ("the first", "extends X") need author sign-off.

## Contract

- **Reads:** the Lean repo's literature docs + docstring `Citation:` lines;
  draft prose; web/arXiv searches.
- **Writes:** paired additions — a `references/extra-biblio.xml` entry + citing
  fragment in `content/insertions/` (priority claims go through directives
  instead).
- **Gate:** `references.py` — no orphan entries, no dangling cites.
- **Provenance:** `Generated-by: <model-id>` trailer; the commit message records
  where the work was located.

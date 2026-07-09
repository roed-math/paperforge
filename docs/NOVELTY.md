# The novelty pipeline

Producing the *inputs* for the introduction's novelty exposition — the
component most often missing from LLM-generated mathematical text, because it
requires knowledge of the surrounding literature. The deliverable is a
**claims dossier** (`novelty/claims.json`), not prose: typed, evidence-backed,
literature-checked claims with author sign-off states. The intro-novelty
skill writes prose ONLY from approved claims.

## The five novelty classes and their evidence sources

| class | claim shape | machine evidence | human share |
|---|---|---|---|
| 1. novel method | "technique T has no earlier instance on topic X" | targeted literature searches (recorded); absence in local reference PDFs | high — absence-of-evidence judgment |
| 2. surprising result | "R contradicts the expectation E from [W]" | contrast language in the paper; census history (axioms expected, then discharged); literature statement of E | highest — what counts as "expected" |
| 3. weakened hypotheses | "R holds under H' ⊊ H of [W, Thm T]" | **nearly formal**: the Lean statement's hypothesis list vs the literature statement's; `lean_minimal_hypotheses` for what the proof actually uses | low — confirm the comparison is fair |
| 4. generalizable definition | "D is not specific to this problem" | **signature genericity** (does the Lean def mention instance constants like `ℚ_[2]`?); fan-in from the dependency graph | medium — where else it could apply |
| 5. cross-field ingredient | "tool I comes from field F ≠ this paper's" | Mathlib import-area profile of the formalization; concept vocabulary | low — field attribution is usually clear |

Class 3 is the formalization's superpower: hypotheses in Lean are
machine-readable, so "we need less than the literature" is a *checkable* claim.
Class 2 is the least mechanizable and the most valuable — the pipeline's job is
to surface *candidates* (the paper's own contrast language; foundations that
turned out lighter than expected), never to decide alone what is surprising.

## Pipeline stages

1. **Evidence collection** (`ingest/novelty_evidence.py`, deterministic) →
   `novelty/evidence.json`:
   - novel-node inventory: the `novel` entries of `formalized-known.json` +
     the paper-nodes section of the Lean repo's reviewer enumeration;
   - definition genericity: for each novel `def`/`structure`, whether its
     signature mentions instance-specific constants, and its dependency
     fan-in (from the atlas graph) — high fan-in + generic signature =
     class-4 candidate;
   - contrast-language scan of the paper (exceptional / in contrast / fails /
     resisted / cannot / surprisingly / unlike) with block tags — class-2
     seeds;
   - census-history events (axioms discharged, hypotheses dropped during
     formalization) — class-2/3 seeds;
   - Mathlib import-area histogram — class-5 seeds;
   - method-unit seeds: section/subsection titles + module-doc headlines.
2. **Claim drafting + literature verification** (LLM): for each seed, draft a
   typed claim and *check it*: local reference PDFs first (does NSW/Serre
   already do this?), then targeted web/arXiv searches. Record every query
   and its outcome in the claim — an unverifiable-absence claim is stated as
   such ("we found no earlier instance", not "this is the first").
3. **The dossier** (`novelty/claims.json`): each claim has `class`,
   `statement`, `evidence` (pointers into evidence.json + literature record),
   `paper_anchors` (tags), `confidence`, `status:
   proposed | author-approved | author-rejected | needs-discussion`.

   **Statements are render-ready claim markup**, not informal prose: `<m>…</m>`
   for math (the paper's macros are available), `[@bib-KEY]` or
   `[@bib-KEY, pin]` for citations by exact bibliography key (this is what
   disambiguates e.g. the two Serre entries), `<c>`, `<em>`, `<ndash/>`.
   What the author approves is what gets typeset — the render step performs
   no linguistic conversion. The review dashboard shows a live typeset
   preview with citation chips (hover = the full bibliography entry; unknown
   keys are flagged red) and an insert-citation picker.

   A claim that cites a work not yet in the bibliography carries it in
   `new_refs: {key: <biblio entry markup>}`. These entries materialize into
   `references/extra-biblio.xml` only when the claim is approved and
   rendered — so the no-uncited-entries gate stays green while the claim is
   pending.
4. **Author review** — the gate. Novelty claims are never auto-published.
5. **Prose** (intro-novelty skill): writes the introduction's novelty
   paragraphs from approved claims only, citing the works named in the
   evidence; every sentence traceable to a claim id.

## Design principles

- **Hedge by construction**: class-1/2 claims are absence claims; the dossier
  stores the search record so the author can judge the search's adequacy.
- **The verification loop can demote**: a "novel method" seed that turns out
  classical (e.g. character-sum counting of homomorphisms is Frobenius, 1896)
  becomes a class-5 *ingredient* claim or is rejected — with the discovery
  recorded, which is itself useful for the related-work paragraph.
- **Incremental**: seeds are keyed by stable ids (decl names, block tags);
  re-runs only surface new seeds; author decisions are never overwritten.

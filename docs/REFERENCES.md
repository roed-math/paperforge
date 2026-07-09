# The references framework

Two complementary processes with different directions of flow:

1. **Literature connections** (outbound, generative): find work the paper
   should acknowledge — prior work, applications, context — and add citing
   prose to the introduction. The proof does not depend on these.
2. **Citation completeness** (inbound, checking): every fact the paper *rests
   on* is actually cited. The formalization makes this unusually checkable:
   the Lean axiom census IS the list of unproven inputs.

Both respect the math convention enforced by a validator: **no bibliography
entry may exist that is not cited in the text**, and no citation may dangle.

## Artifacts (all committed, all survive re-ingestion)

| artifact | produced by | consumed by |
|---|---|---|
| `references/extra-biblio.xml` | literature-connections skill (+author) | tex2ptx `--extra-biblio` → merged into `<references>` |
| `content/insertions/*.ptx` | skills (connection prose, later: summaries) | tex2ptx `--insertions` → merged at anchor tags |
| `crosswalk/axiom-citations.json` | `ingest/lean_axioms.py` (from the Lean repo) | `references` validator |
| `references/bib-aliases.json` | seeded by extractor, author-corrected | `references` validator (work-name → bib key) |
| `references/citation-needs.json` | citation-audit skill (LLM decisions) | `references` validator (worklist bookkeeping) |
| local PDFs in `references/` | author | pin verification, plagiarism |

The insertion mechanism is the same answer as lean badges and notation wraps:
content that must survive re-ingestion is merged at ingest from sidecar
artifacts, never hand-edited into `source/`.

## Process 1 — literature connections (skill: `literature-connections`)

1. **Candidate mining**, from strongest signal to weakest:
   - the Lean repo's citation discipline (`docs/literature-axioms.md`,
     docstring `Citation:` lines) — works the formalization already leans on;
   - the draft's own bibliography and prose mentions (named results without
     bib entries);
   - web/arXiv search on the paper's subjects (prior presentations of local
     Galois groups, Demushkin theory, applications of explicit presentations).
2. **Judgment per candidate**: classify (prior-work / method / application /
   context), decide whether the connection is real and worth a sentence, and
   draft 1–3 sentences of intro prose with the citation.
3. **Output**: a `<biblio>` entry appended to `references/extra-biblio.xml` +
   an insertion fragment targeting the introduction (or a directive for author
   review first — preferred for anything with a novelty claim). Generated
   prose goes through the plagiarism validator like all generated prose.
4. **Enforcement**: the unused-entry validator guarantees every added entry has
   citing text; the dangling-cite validator guarantees the reverse.

## Process 2 — citation completeness

### Deterministic core (validator `references.py`)

- **Unused bibliography entries** — error. (Math convention; also keeps
  process 1 honest.)
- **Dangling citations** — `<xref ref="bib-K">` with no `<biblio xml:id>`.
- **Axiom coverage** — the heart. `lean_axioms.py` extracts every Lean `axiom`
  with its census label (`**[Classical — B4.]**`), its `Citation:` lines
  (work + precise pin), and its `Paper:` anchors (v428 numbering, resolved to
  stable tags via the crosswalk). The validator then checks, per axiom:
    * the docstring names at least one literature work (else: formalization-side
      warning);
    * each cited work resolves to a bib entry via `bib-aliases.json` (else:
      **the paper's bibliography is missing a work the formalization rests
      on** — error);
    * every resolved paper-anchor block (or its enclosing division) contains a
      citation to that work (else: **the paper states a fact the formalization
      axiomatizes, without citing it there** — error).
- **Pin verification (stage 1)** — pins like `[NSW, Theorem (7.5.11)]` in the
  paper are searched in the local PDF text (pdftotext cache): the pinned
  identifier must occur. Unresolvable pins are warnings that narrow the human
  stage-2 read; this never replaces it.

### LLM half (skill: `citation-audit`)

Facts needing citations that are NOT axioms (background theory recalled in
prose, named theorems, prior definitions). Deterministic lexicon extraction
(capitalized names near theorem/classification/duality/formula, "well known",
"classical", "standard") produces a worklist of blocks; the LLM classifies
each: `needs-citation` (which work) / `cited-nearby` / `common-knowledge`.
Decisions cached block-grain in `references/citation-needs.json` — same
pattern as notation disambiguation: committed, reviewable, incremental under
draft updates. `needs-citation` decisions become directives/insertions, not
silent edits.

## Why the formalization makes this strong

A paper ordinarily has no machine-readable list of what it assumes. Here the
Lean census (currently ~13 axioms, shrinking) is exactly that list, each with
a hand-verified citation pinned to a page in a PDF the repo carries. The
validator turns "did we cite our foundations?" from an editorial hope into a
CI check — and when the axiom-removal work discharges an axiom, the check
adapts automatically on the next extraction.

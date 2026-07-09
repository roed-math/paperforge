# Architecture

## Inputs, outputs, source of truth

**Inputs** (paths in `paper.toml`; both are moving targets):
- an AI-written paper in LaTeX,
- a Lean formalization (a lake project).

**Source of truth:** a PreTeXt document, authored/maintained by Claude.

**Outputs:**
- arXiv-ready LaTeX + PDF (PreTeXt `latex` / `pdf` targets),
- structured HTML (PreTeXt `html` target + the enhancement layer in
  `pretext-template/`).

Why PreTeXt and not LaTeX-as-truth: detail levels want an attribute-bearing
format, PreTeXt ships knowls, and the LLM-author erases the usual XML-authoring
pain. The arXiv LaTeX is treated as generated output. (Full rationale lives in the
project memory; this is the decision, not the debate.)

## The two-layer model

```
            AI LaTeX draft            Lean project
                  |                        |
          [ingest-draft skill]        (referenced by <lean> refs)
                  |                        |
                  v                        |
        +----------------------+           |
        |  PreTeXt source      |<----------+
        |  (source of truth)   |
        +----------------------+
             |            |
   generative passes   deterministic validators
   (skills, re-runnable) (Python, CI-gating)
             |            |
             v            v
        +----------------------+
        |  PreTeXt source      |  <-- converges
        +----------------------+
             |            |
        build html    build latex/pdf
             |            |
             v            v
        structured     arXiv
          HTML
```

**Validators never write; skills never gate.** A validator failing means "a human
or a skill must fix something"; it does not auto-edit. This keeps every change
attributable (see [DIRECTIVES.md](DIRECTIVES.md), [PLAGIARISM.md](PLAGIARISM.md)).

## Requirement map

The original 12 requirements, each assigned to a mechanism:

| # | Requirement | Mechanism | Where |
|---|---|---|---|
| 1 | AI paper + formalization as inputs | config paths | `paper.toml` |
| 2 | Style corpus + writing advice | corpus dir, fed to skills | `style-corpus/`, `paper.toml` |
| 3 | Plagiarism guard | **validator** + human review | `validators/plagiarism.py`, [PLAGIARISM.md](PLAGIARISM.md) |
| 4 | Detail level (default + interactive) | PreTeXt `@detail-level`/`component` + HTML slider | `pretext-template/`, [HTML-FEATURES.md](HTML-FEATURES.md) |
| 5 | Bridging text between results | **skill** | `skills/bridge-text` |
| 6 | Section summaries (difficulty-graded) | **skill** + presence **validator** | `skills/section-summaries`, `validators/section_summaries.py` |
| 7 | Novelty/interest language in intro | **skill** | `skills/intro-novelty` |
| 8 | Notation defined before used | **validator** + hover feature | `validators/notation_order.py`, `pretext-template/` |
| 9 | Grammar pass | **skill** | `skills/grammar-pass` |
| 10 | Reference check vs local PDFs | **validator** (stage 1) + human (stage 2) | `validators/references.py`, `references/` |
| 11 | Feedback / background additions | **skill** + stale-target **validator** | `skills/apply-directives`, `validators/directives.py`, [DIRECTIVES.md](DIRECTIVES.md) |
| 12 | Links to the formalization | `<lean>` feature + `checkdecls` **validator** | `pretext-template/xsl/`, `validators/lean_links.py` |

## Moving-target strategy

Both inputs evolve after the first arXiv post. The framework stays robust because
every cross-reference is a *checkable* handle:

- `<lean ref="Namespace.decl">` — validated against the current Lean project's
  declaration list (`lean_links.py`, a `checkdecls` analog). A Lean refactor that
  renames a decl fails the build instead of silently rotting.
- `xml:id` — directives and internal references target ids; `directives.py` fails
  on a directive whose target id no longer exists.
- notation keys — `notation_order.py` verifies use-after-definition against the
  current source.

So "improve the formalization, rebuild the paper" is a validator run, not a manual
audit. Re-running any skill or validator is idempotent; skills consume their inputs
(directives) and record changes as discrete git commits.

## Pipeline stages

1. **ingest** — `ingest-draft` converts the AI LaTeX into PreTeXt structure.
2. **generative passes** — `bridge-text`, `section-summaries`, `intro-novelty`,
   `grammar-pass`, `apply-directives`. Each is independently re-runnable.
3. **validate** — `python -m paperforge_validators.run_all` (CI gate).
4. **build** — `pretext build web` and `pretext build print`.

Stages are not a strict pipeline: because inputs move, you re-enter at any stage.
Validators are the invariant that must hold before a build is shippable.

## Repo relationship

The tool provides *behavior* (skills), *checks* (validators), and *scaffolding*
(`pretext-template/`, `templates/`). An instance provides *content* + *config*.
`paper-init` stamps a new instance from the templates. Lessons from the first
instance (G_Q2) are ported back here by generalizing a skill or validator and
deleting the instance-specific copy.

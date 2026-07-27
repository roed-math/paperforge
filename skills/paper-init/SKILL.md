---
name: paper-init
description: Bootstrap a new paperforge instance — run the deterministic `paperforge init`, then help the author with the judgment calls (config choices, inputs, first bootstrap review).
---

# paper-init

The scaffolding itself is `paperforge init` — deterministic, tested, and
self-checking. This skill wraps it with the judgment work. Do NOT copy or
edit scaffold files by hand; if the initializer's output is wrong, fix the
initializer.

## Steps

1. Confirm the cwd is an empty/new repo intended for one paper, then run
   `paperforge init . --non-interactive` with the flags the author's
   answers imply (`--title`, `--slug`, `--draft`, `--lean-root` +
   `--lean-project-name`, or `--no-lean`; `--mathbb`; `--site` when a
   project site is wanted). Inspect its report; a WARN about the PreTeXt
   core means run `paperforge doctor` after installing pretext.
2. Interview for the judgment-bearing config `init` cannot guess, and edit
   `paper.toml` accordingly (docs/CONFIGURATION.md): the formalization's
   `module` and `docs_root`, `[ingest] authors`, any
   `[[ingest.literal_rewrites]]` for structural draft macros, detail
   levels, a `badge_cap` for decomposed-proof projects.
3. Have the author drop the inputs (draft, style corpus, reference PDFs),
   then run `paperforge doctor` and fix anything it flags.
4. Run `paperforge ingest --bootstrap` and REVIEW the candidate
   declaration map WITH the author — the mining is heuristic and
   acceptance is the author's call (`paperforge accept lean-decl-map`).
5. First `paperforge build web` + `paperforge check`; the validator
   findings on a fresh paper are the worklist for the generative skills,
   not noise. Hand off to `ingest-draft` refinements and the content
   passes.

## Contract

- **Reads:** the author interview; `paperforge init`/`doctor` output.
- **Writes:** `paper.toml` judgment edits; nothing the initializer owns.
- **Gate:** `paperforge doctor` exit 0; the bootstrap review completed
  with the author.
- **Provenance:** the scaffolding commit records the paperforge version
  (build provenance carries the exact commit thereafter).

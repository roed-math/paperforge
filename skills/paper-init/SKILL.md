---
name: paper-init
description: Scaffold a new paperforge instance — copy the PreTeXt template and config into the current (empty) repo, then help fill in paper.toml.
---

# paper-init

Bootstraps an instance repo from the tool's templates.

## Steps
1. Confirm the cwd is an empty/new repo intended for one paper.
2. Copy `pretext-template/` → `source/`, `xsl/`, `publication/`, `web-assets/`,
   `project.ptx`; copy `templates/paper.toml` → `./paper.toml`; create
   `style-corpus/`, `references/`, `directives/`, `directives/applied/`,
   `inputs/draft/`.
3. Interview the author for `paper.toml` values: title, AI-draft path, Lean
   project path, `lean_docs_base`, detail `default_level`/`max_level`.
4. Fill the placeholders from config:
   - `xsl/custom-html.xsl`: `@@PRETEXT_CORE_XSL@@`, `lean.docs.base`;
   - `xsl/print-latex.xsl` / `xsl/arxiv-latex.xsl`:
     `@@PRETEXT_CORE_LATEX_XSL@@` / `@@PRETEXT_CORE_LATEX_CLASSIC_XSL@@`
     (siblings of `pretext_core_xsl` in the installed core);
   - copy `templates/build-web.sh` -> `scripts/build-web.sh` and fill
     `@@PAPERFORGE_ROOT@@`, `@@AI_DRAFT@@`, `@@LEAN_ROOT@@`,
     `@@MATHBB_LETTERS@@`; create `notation/`, `content/insertions/`,
     `references/extra-biblio.xml` skeletons.
5. Print the next commands: drop the AI draft + style corpus + reference PDFs, then
   run `ingest-draft`.

## Notes
- Never overwrite existing content without confirmation.
- The instance keeps a pinned reference to the tool version used.

## Contract

- **Reads:** the paperforge checkout (`pretext-template/`, `templates/`); the
  author interview for `paper.toml` values.
- **Writes:** the instance scaffold (`source/`, `xsl/`, `publication/`,
  `paper.toml`, `scripts/build-web.sh`, empty sidecar dirs).
- **Gate:** `pretext build web` succeeds in the stamped instance.
- **Provenance:** the scaffolding commit records the paperforge version; no
  generator stamp (nothing is proposed).

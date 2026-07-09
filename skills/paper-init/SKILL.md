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
4. Set the `lean.docs.base` XSL param and the core-XSL import path in
   `xsl/custom-html.xsl` from config (see the HTML-FEATURES follow-up on the
   portable import path).
5. Print the next commands: drop the AI draft + style corpus + reference PDFs, then
   run `ingest-draft`.

## Notes
- Never overwrite existing content without confirmation.
- The instance keeps a pinned reference to the tool version used.

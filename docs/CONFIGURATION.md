# Configuration reference

Three layers, merged in order (later wins):

1. **`paper.toml`** — committed; the instance's durable choices.
2. **`.paperforge.local.toml`** — gitignored; machine-local values.
3. **CLI flags / environment** — per-invocation.

Path rule (one authoritative interpretation): relative paths in either
config file are **relative to the instance root**; `~` expands; absolute
paths pass through; URL-valued keys (`docs_root`) never touch filesystem
resolution. `paperforge check /path/to/instance` behaves identically to
running it inside.

## [paperforge]

| key | default | meaning |
|---|---|---|
| `instance_schema` | 1 | the config/artifact-layout generation. Checked on every load; an unsupported value fails with "update the tool or migrate". This is the routine compatibility gate — deliberately NOT a git-commit pin (docs/DEVELOPMENT.md). |

## [paper]

| key | default | meaning |
|---|---|---|
| `title` | — | the paper's title (display) |
| `slug` | directory name | short identifier for outputs |
| `document_id` | slug | PreTeXt `<document-id>` |
| `instance_name` | — | **deprecated** alias of `slug` |

## [inputs]

| key | default | meaning |
|---|---|---|
| `ai_draft` | `inputs/draft/main.tex` | the LaTeX draft (a canonical editable input) |
| `lean_project`, `lean_module`, `lean_docs_base`, `lean_project_name` | — | **deprecated** primary-formalization keys; normalized into `[formalizations.primary]` (run `paperforge migrate config`) |
| `[inputs.formalizations.<name>]` | — | **deprecated** table for additional projects; same record shape as below |

## [formalizations.<key>] (normalized shape; `primary` sorts first)

| key | default | meaning |
|---|---|---|
| `name` | the key | badge project name (`lean-proj-<name>` CSS, `/lean/<name>/` docs subset) |
| `root` | — | local checkout (path) |
| `module` | — | top module dir inside root (census/docs subset) |
| `docs_root` | — | deployed docs URL prefix (**URL**, not a path) |
| `declmap` | `crosswalk/lean-decl-map.json` | the ACCEPTED tag→decl map; bootstrap writes `*.candidate.json` beside it |
| `badge_cap` | — | at most N badges per statement for this project |

## [ingest]

| key | default | meaning |
|---|---|---|
| `mathbb_letters` | "" | restyle `\mathbf X`→`\mathbb{X}` for these letters |
| `numbering_profile` | `amsart-shared-section-theorems-global-equations` | the named numbering convention; the simulator refuses others |
| `authors` | [] | repeatable tex2ptx author specs (`'Name|Affil line|...'`, `'@draft'` positions the draft's own author) |
| `axioms_old_matched`, `axioms_old_numbering` | — | old-snapshot maps for the axiom census's historical anchors |
| `[[ingest.literal_rewrites]]` `from`/`to` | [] | structural draft macros expanded before parsing (logged; the macro's definition is dropped from the emitted block) |

## [style], [references], [notation], [detail], [plagiarism]

As in `templates/paper.toml` (the annotated catalogue) — corpus/advice
paths; reference `pdf_dir`/`bib`/`labels`; notation `far_words`, hover
delays, `prose_map`; detail tiers; plagiarism `ngram`/`error_run`/`sources`.

## [build]

| key | default | meaning |
|---|---|---|
| `web_output` / `print_output` | `output/web` / `output/print` | build dirs |
| `pretext_core_xsl` | discovered | machine-local — put it in `.paperforge.local.toml`; instances scaffolded by `paperforge init` import gitignored `xsl/core-local/` shims that init/doctor regenerate from this |
| `[[build.web_substitutions]]` `from`/`to` | [] | literal replacements on built pages (e.g. Unicode for raw title math in HTML metadata) |

## [validators.*], [trust_table], [site], records config

Subsystem blocks passed through raw: validator waivers
(`[validators.section_summaries].exempt`), the trust-base table, the
`[site]` family (docs/DEPLOYMENT.md), and the records pipelines' own JSON
config (the first instance's `records-pipeline/` is the worked example;
the per-pipeline config shapes are in the `records/` module docstrings).

## Examples

Zero formalizations: omit every formalization table — badges, census, and
`lean_links` all skip.

One: `[formalizations.primary]` with `name`/`root` (+ `module`, `declmap`).

Two: add `[formalizations.<name>]` with `badge_cap` when its proof style
decomposes statements into many declarations, and give it a badge color
in `web-assets/detail-ui.css` (a commented example sits at the
`lean-proj-` rules). The first instance runs two projects on the old
shape, normalized on load.

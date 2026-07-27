# Getting started: a second paper

The deterministic spine is the `paperforge` command; the generative passes
(summaries, bridging, novelty, grammar) are agent-executed skills layered
on top. This guide walks the milestones; every step's failure modes are in
[TROUBLESHOOTING.md](TROUBLESHOOTING.md), every config key in
[CONFIGURATION.md](CONFIGURATION.md).

## 1. Install the tool

```bash
git clone https://github.com/roed-math/paperforge
python3 -m pip install -e paperforge -e paperforge/validators
```

Host requirements (`paperforge doctor` checks all of this for you):

| need | why |
|---|---|
| Python ≥ 3.11 with `lxml`, `pyyaml` | the tool itself |
| PreTeXt CLI (2.43.x exercised) | the builds |
| TeX Live + `latexmk` | the arXiv/print PDFs |
| `pdftotext` (poppler) *(optional)* | plagiarism + reference pin checks |
| `xsltproc` + `xmllint` *(optional)* | the author-metadata step |
| `node`/`npm`, `rsvg-convert`, `pymupdf` *(optional)* | offline MathJax, favicon rasters, PDF page counts |

**One interpreter rule**: the `python3` on `PATH` must be the one with the
packages, for every session.

## 2. Create the instance

```bash
mkdir my-paper && cd my-paper && git init
paperforge init . --title "My Paper" --slug my-paper \
    --lean-root ../my-paper-lean          # or --no-lean
```

Deterministic and self-checking: scaffold, valid empty sidecars,
`.gitignore`, a minimal `paper.toml` (with its `instance_schema`), and no
unresolved placeholders — machine-local values (the PreTeXt core XSL) land
in gitignored `.paperforge.local.toml` + `xsl/core-local/` shims, never in
committed files. Then put your inputs in place:

- the AI-written LaTeX draft at `inputs/draft/main.tex`;
- prior papers (LaTeX preferred) under `style-corpus/`
  (`ingest/fetch_arxiv_corpus.py` can pull them from arXiv);
- PDFs of the works you cite under `references/`.

## 3. Diagnose

```bash
paperforge doctor
```

Grouped, actionable: environment, config, the tool checkout in use
(commit + dirty state), the derived instance state, and the one next
command. Exit 0 means nothing blocks.

## 4. Bootstrap

```bash
paperforge ingest --bootstrap
```

First-run ingestion needs no declaration map: it converts the draft,
writes `crosswalk/numbering-current.json` and the source map, and — when a
formalization is configured — mines a **candidate** declaration map:

```text
Bootstrap ingestion completed.
Created:
  crosswalk/numbering-current.json
  crosswalk/lean-decl-map.candidate.json

Review the candidate declaration map(s), then:
  paperforge accept lean-decl-map
  paperforge build web
```

## 5. Review the candidate, accept deliberately

The mining is heuristic (declaration names, docstring citations) — that is
why builds refuse to use a candidate silently. Each entry carries its
evidence (`via`, `file`, `line`, `cited`); prune wrong matches, then:

```bash
paperforge accept lean-decl-map        # per --formalization for others
```

## 6. First build + validators

```bash
paperforge build web
paperforge check
```

The build lists every stage with a skip *reason* for unconfigured ones
("not configured" is never conflated with "file missing"), runs the
portable postprocessing (lazy MathJax, ToC default-open), and writes
`output/build-provenance.json`. `paperforge check` runs the eight
validators; on a fresh paper, missing section summaries and early notation
uses are *real findings* — the worklist for the skills.

## 7. The generative passes (agent territory)

Run through your agent in roughly this order: `ingest-draft` refinements,
`bridge-text`, `section-summaries`, `intro-novelty` (from the approved
claims dossier), `background-sections`, `grammar-pass` last. Author
control runs through **directives** ([DIRECTIVES.md](DIRECTIVES.md)) and:

```bash
paperforge review        # the dashboard + paper-view editor, one server ever
```

## 8. PDF and the optional site

```bash
paperforge build arxiv --pdf
```

Site assembly, deployment, version footers, and the records pipelines are
config-gated extras — [DEPLOYMENT.md](DEPLOYMENT.md). Each lights up only
when its `[site]`/`[trust_table]`/records block exists.

## Where things live

```
paper.toml            committed config    .paperforge.local.toml  machine-local
inputs/draft/         the LaTeX draft (canonical, editor-spliced)
source/               GENERATED PreTeXt — never hand-edit
content/              survives re-ingestion: insertions/, authors.xml
crosswalk/            numbering, source map, decl maps, axiom census
notation/ references/ directives/ novelty/ style-corpus/   sidecars
output/               builds + provenance (gitignored)
```

The cardinal rule: **`source/` is generated.** Prose changes go through
the draft (paper-view editor or LaTeX); persistent additions through
`content/insertions/`.

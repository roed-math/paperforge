# Getting started: a second paper

paperforge has one fully-exercised instance (the G_Q2 paper). This is the
honest path to instance number two. The framework's working assumption is
that **Claude Code (or a comparable agent harness) is the operator**: the
generative steps are skills — instruction files the agent executes — not
installed programs. The deterministic layer (converter, validators, build
scripts) runs fine without any agent.

## 0. Host requirements

| need | why | check |
|---|---|---|
| Python ≥ 3.11 with `lxml`, `pyyaml` | validators, ingest, sitegen | `python3 -c "import lxml, tomllib"` |
| PreTeXt CLI (2.43.x exercised) | the builds | `pretext --version` |
| TeX Live + `latexmk` | the arXiv/print PDFs | `latexmk --version` |
| `pdftotext` (poppler) | plagiarism + reference pin checks | `pdftotext -v` |
| `xsltproc` + `xmllint` (libxslt) | author-metadata step | `xsltproc --version` |
| `node`/`npm` *(optional)* | vendored MathJax for the offline review server; the favicon's font outlines | `npm -v` |
| `rsvg-convert` *(optional)* | favicon .ico / touch-icon rasters | `rsvg-convert -v` |
| `pymupdf` *(optional)* | PDF page count in the version footer | `python3 -c "import fitz"` |

**One interpreter rule**: whichever `python3` has `lxml` must be the one on
`PATH` for every build (a conda/homebrew/system split here has burned real
time — scripts that spawn subprocesses lead `PATH` with
`Path(sys.executable).parent` for this reason). Put it first in `PATH` and
keep it there.

One-time, from the paperforge checkout:

```bash
pip install -e validators/     # installs the `paperforge-check` gate command
```

## 1. Scaffold the instance

Create an empty git repo for the paper. In it, with the paperforge checkout
at a known path (`$PF` below), have your agent follow
`$PF/skills/paper-init/SKILL.md`: it copies `pretext-template/` and
`templates/` into place, interviews you for `paper.toml` values, and fills
the `@@PLACEHOLDER@@` params (paths to your AI draft, your Lean project,
the installed PreTeXt core XSL — currently an absolute path, see
Limitations in the README).

Then drop in your inputs:

- the AI-written LaTeX draft at `[inputs] ai_draft`;
- your prior papers (LaTeX preferred) under `style-corpus/`
  (`$PF/ingest/fetch_arxiv_corpus.py` can pull them from arXiv);
- PDFs of the works you cite under `references/`.

## 2. The loop

```bash
scripts/build-web.sh      # trust table -> ingest -> author metadata ->
                          # axiom census + drift gate -> far marks ->
                          # pretext build web -> hover registries
paperforge-check          # the eight validators; exit 1 on any error
```

Generative passes are skills, run through your agent in roughly this order:
`ingest-draft` (once, and after draft updates), then `bridge-text`,
`section-summaries`, `intro-novelty` (from the approved claims dossier),
`background-sections`, `grammar-pass` last. Author control runs through
**directives** (docs/DIRECTIVES.md) and the **review dashboard**:

```bash
python3 $PF/review/review_server.py     # http://127.0.0.1:8765/review
```

— one server per instance, ever. The paper view doubles as the editor
(docs/EDITOR.md): ✎ on every statement, proof, and paragraph.

PDFs, when wanted:

```bash
pretext build arxiv && (cd output/arxiv && latexmk -pdf main.tex)
```

## 3. What's optional (config-gated)

Everything below is off until its config block exists, so a minimal
instance ignores this table entirely.

| paper.toml block | turns on |
|---|---|
| `[inputs.formalizations.<name>]` | additional formalization(s): per-project badges, docs subsets, validation |
| `[trust_table]` | the intro trust-base table + its drift gate |
| `[validators.section_summaries]` | recorded waivers for deliberately summary-less sections |
| `[site]` + `web-assets/site/` | the project site (`scripts/build-site.sh`, `scripts/deploy.sh [--test]`) |
| `[site.status]` + a site `status.json` | stamped version footers + the drift gate |
| `[site.bg_knowls]` | homepage knowls (background clusters, statement panels) |
| `[site.favicon]` | favicon generated from the paper's own typeface |
| records config (separate file, see below) | development-record pipelines: token ledger, sanitized session corpora, dashboard |

The records pipelines read their own JSON config (session include-lists +
dashboard identity), not paper.toml:
`python3 $PF/records/run_all.py <records-config.json>`. The worked example
is gq2-paper's `records-pipeline/` (config + README).

## 4. Where things live

An instance after a few passes:

```
paper.toml            config (the only file the tools read for knobs)
inputs/draft/         the AI LaTeX draft (byte-preserved; edits splice in)
source/               GENERATED PreTeXt — never hand-edit; regenerate
content/              survives re-ingestion: insertions/, authors.xml
crosswalk/            numbering maps, decl maps, axiom census, source map
notation/             notation-map.json + sense decisions
references/           PDFs, extra-biblio, trust annotations, PROVENANCE.md
directives/           the author's queue: directives, marks, edit-undo
novelty/ followups/   claims dossiers (dashboard-reviewed)
style-corpus/         your prior papers + ADVICE.md
web-assets/           hover UI + fonts (+ site/ if you build one)
scripts/              thin wrappers calling $PF tools
output/               builds (gitignored)
```

The cardinal rule twice, because it is the one people break: **`source/`
is generated**. Content you add by hand goes in `content/insertions/`
(merged at ingest, survives every re-ingestion); edits to existing prose
go through the paper-view editor or directives, which splice the draft
and regenerate.

## 5. When something fails

- `paperforge-check` failing is the system working: each finding names the
  validator and the fix path. `artifact_drift` findings mean "rerun the
  named generator and commit" (build-web/build-site do this).
- A `<lean>` badge erroring in `lean_links` after a formalization update:
  follow `skills/update-formalization/SKILL.md` — the bump checklist.
- The build works but hovers/knowls misbehave: docs/HTML-FEATURES.md
  carries the feature contracts, and the verification gotchas live in the
  paperforge HANDOFF.

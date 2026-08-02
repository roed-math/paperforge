# Getting started

From an empty directory to a built, validated paper. Everything here is
deterministic and copy-pasteable: the `paperforge` command does the
judgment-free work, and the generative passes (summaries, bridging prose,
novelty, grammar) are agent-executed skills layered on top.

Failure modes for every step are in [TROUBLESHOOTING.md](TROUBLESHOOTING.md);
every config key is in [CONFIGURATION.md](CONFIGURATION.md).

**What you need before starting:** a LaTeX draft of the paper (amsart-ish),
and optionally a Lean project formalizing some of it. Neither has to be
finished — the whole point is that both are moving targets.

---

## 1. Install the tool

```bash
git clone https://github.com/roed-math/paperforge
python3 -m pip install -e paperforge -e paperforge/validators
```

Editable installs, deliberately: you will end up fixing the tool while
writing the paper, and an editable checkout means no reinstall step
([DEVELOPMENT.md](DEVELOPMENT.md)).

Host requirements — `paperforge doctor` checks every one of these and tells
you what each is for:

| need | why | blocking? |
|---|---|---|
| Python ≥ 3.11 with `lxml`, `pyyaml` | the tool itself | yes |
| PreTeXt CLI (2.43–2.45 exercised) | the HTML and LaTeX builds | yes |
| TeX Live + `latexmk` | the arXiv/print PDFs | only for PDFs |
| `xsltproc` + `xmllint` | the author-metadata step | only with author records |
| `pdftotext` (poppler) | plagiarism + reference-pin checks | no, degrades |
| `node`/`npm`, `rsvg-convert`, `pymupdf` | offline MathJax, favicon rasters, PDF page counts | no, degrades |

On macOS the usual snag is that `/usr/bin/python3` is Xcode's, not the one
holding your packages. **One interpreter rule:** the `python3` first on
`PATH` must be the one you installed into, in every session. `paperforge
doctor` prints which interpreter it is running under; if that line surprises
you, fix `PATH` before going further. (Homebrew and conda users: put that
`bin` directory first in your shell profile, not just in one terminal.)

## 2. Verify the install before touching your paper

```bash
paperforge selftest
```

This runs the entire sequence below against the bundled fixture
([examples/minimal-paper](../examples/minimal-paper)) in a scratch directory
and deletes it afterwards. It takes under a minute and answers "is my
environment right?" separately from "is my paper right?" — which is the
question you actually want answered on day one.

```text
PaperForge selftest

  scratch: /tmp/paperforge selftest 4gk1p0/…

  ok    init
  ok    doctor
  ok    ingest --bootstrap
  ok    build web refuses an unreviewed candidate map
  ok    accept lean-decl-map
  ok    status
  ok    build web
  …
All steps passed — the install is working.
```

Add `--keep` to inspect the scratch instance, or `--no-build` to skip the
PreTeXt build.

## 3. Create the instance

One repository per paper; the tool repo holds no paper content.

```bash
mkdir my-paper && cd my-paper && git init
paperforge init . --title "My Paper" --slug my-paper \
    --lean-root ../my-paper-lean      # or --no-lean
```

Useful flags: `--lean-project-name` (the badge project key, default: the
Lean root's directory name), `--mathbb QZ` (restyle `\mathbf Q` → `\mathbb{Q}`),
`--site` (also scaffold a project-site homepage), `--non-interactive`.

`init` is deterministic and self-checking: it copies the scaffold, fills
every placeholder, creates each sidecar the build assumes (valid and empty),
writes a conservative `.gitignore` and a minimal `paper.toml`, and verifies
that nothing is left unresolved. Machine-local values — the PreTeXt core XSL
location — land in a gitignored `.paperforge.local.toml` plus
`xsl/core-local/` shims, never in a committed file.

Then put your inputs in place:

- the LaTeX draft at `inputs/draft/main.tex`;
- your **own** prior papers under `style-corpus/` (LaTeX source, not PDFs —
  see the README there; `ingest/fetch_arxiv_corpus.py` pulls them from arXiv);
- PDFs of the works you **cite** under `references/`.

The two directories are not interchangeable: the corpus is a voice to
imitate, the references are sources you must not copy from.

## 4. Diagnose

```bash
paperforge doctor
```

Grouped and actionable: environment, config, which paperforge checkout is
running (commit + dirty state), the derived instance state, and the single
next command. Exit 0 means nothing blocks.

## 5. Bootstrap

```bash
paperforge ingest --bootstrap
```

First-run ingestion needs no declaration map: it converts the draft, writes
`crosswalk/numbering-current.json` and the source map, and — when a
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

**Validate the numbering once, here.** The simulator implements exactly one
convention (`amsart-shared-section-theorems-global-equations`) and refuses
any other name rather than guess. Compile your draft with pdflatex and check
the `\newlabel` numbers in its `.aux` against
`crosswalk/numbering-current.json`. If they disagree, your paper uses a
convention the simulator does not yet implement — fix that before building
anything on top of it.

## 6. Review the candidate map, accept deliberately

The mining is heuristic (declaration names, docstring citations), which is
why builds refuse to use a candidate silently. Each entry carries its
evidence (`via`, `file`, `line`, `cited`); delete the wrong matches, then:

```bash
paperforge accept lean-decl-map
# for a second formalization: --formalization <name>
```

## 7. First build and first validator run

```bash
paperforge build web
paperforge check
```

The build lists every stage with a *reason* for each skip ("not configured"
is never conflated with "file missing"), applies the portable
postprocessing (lazy MathJax, ToC default-open), and writes
`output/build-provenance.json` recording the exact tool commit. Use
`--plan` to see the stage list without touching anything.

`paperforge check` runs the eight validators. **On a fresh paper it will
exit 1, and that is the correct outcome** — the findings are your worklist,
not noise:

| finding | means |
|---|---|
| `section_summaries` | sections have no `<introduction>` yet → the `section-summaries` skill |
| `notation_order` | a symbol is used before its definition → notation map or prose fix |
| `references` | a citation or axiom lacks a locator/parsed citation → `citation-audit` |
| `plagiarism: no readable sources` | no reference PDFs yet → drop them in `references/` |
| `lean_links` | a badge names a declaration that does not exist → regenerate the map |

Open the result and read it:

```bash
paperforge review        # dashboard + the paper view as editor, port 8765
```

**Exactly one review server per instance root, ever** — a second writer can
corrupt the decision artifacts. The command guards with a PID file.

## 8. The generative passes (agent territory)

These are instruction files under `skills/`, executed by an agent (Claude
Code today), each ending in a Contract block naming what it reads, writes,
and is gated by. A sensible order:

1. `ingest-draft` — triage the converter's warnings, settle the structure
2. `bridge-text`, `section-summaries` — the connective prose
3. `intro-novelty` — from the approved claims dossier ([NOVELTY.md](NOVELTY.md))
4. `background-sections` — what the reader needs that the draft assumes
5. `citation-audit` — locator pins, verified against the source PDFs
6. `grammar-pass` — last, once the content has settled

Your control surface throughout is **directives**
([DIRECTIVES.md](DIRECTIVES.md)) plus the review dashboard. House style —
voice, level of detail, things to avoid — goes in `style-corpus/ADVICE.md`,
which every skill reads.

## 9. The PDF

```bash
paperforge build arxiv --pdf
```

Produces `output/arxiv/` (amsart-style LaTeX for submission) and, with
`--pdf`, runs `latexmk` on it. `paperforge build print` is the
full-detail-tier variant.

## 10. Optional: the project site

```bash
paperforge build site
```

Assembles `output/site/` from whatever has been built — the hand-authored
pages from `web-assets/site/`, the paper at `/paper/`, the PDF, Verso
blueprints, doc-gen4 subsets. Missing pieces are named as warnings, so a
partial site still assembles. Version footers, favicons, and the
development-record pipelines are config-gated extras; each lights up only
when its `[site]` / `[trust_table]` / records block exists —
[DEPLOYMENT.md](DEPLOYMENT.md).

---

## Where things live

```
paper.toml            committed config    .paperforge.local.toml  machine-local
inputs/draft/         the LaTeX draft (canonical, editor-spliced)
source/               GENERATED PreTeXt — never hand-edit
content/              survives re-ingestion: insertions/, authors.xml
crosswalk/            numbering, source map, decl maps, axiom census
notation/ references/ directives/ novelty/ style-corpus/   sidecars
web-assets/           the instance's UI layer (CSS/JS), copied into builds
output/               builds + provenance (gitignored)
```

The cardinal rule: **`source/` is generated.** To change existing prose,
edit the draft (the paper-view editor splices it for you); to add persistent
paperforge-only material, use `content/insertions/`.

## Command reference

| command | does |
|---|---|
| `paperforge selftest` | run the fixture end to end; verifies the install |
| `paperforge init [PATH]` | scaffold an instance |
| `paperforge doctor` | environment + instance diagnosis, one next command |
| `paperforge status` | derived state from artifacts on disk |
| `paperforge ingest [--bootstrap]` | draft → generated PreTeXt (+ candidate maps) |
| `paperforge accept lean-decl-map` | promote a reviewed candidate |
| `paperforge build {web,arxiv,site} [--plan] [--pdf]` | the builds |
| `paperforge check` | the eight validators (CI gate) |
| `paperforge review` | the author dashboard + paper-view editor |
| `paperforge migrate config [--check]` | report/rewrite deprecated config keys |

Every command takes the instance root as an optional positional argument;
the default is the nearest ancestor of the cwd containing `paper.toml`.

## If something goes wrong

`paperforge doctor` first — it names the problem and the next command.
Then [TROUBLESHOOTING.md](TROUBLESHOOTING.md), which covers interpreter
mismatches, a missing PreTeXt core XSL, first-build states, numbering
mismatches, drift gates, HTML enhancement failures, and how to collect a
diagnostic bundle for a bug report.

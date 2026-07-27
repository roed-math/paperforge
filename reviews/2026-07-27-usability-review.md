# PaperForge usability review and implementation handoff

**Repository:** `roed-math/paperforge`  
**Review target:** the `master` branch as inspected on 2026-07-27, including commit `63327e5b49257a7d58d6850a0fa6505be20b1e16` (“README rewrite + a getting-started path for a second instance”)  
**Primary purpose of this document:** give a local coding agent enough context, design direction, file-level guidance, and acceptance criteria to make PaperForge dependable for starting a second paper project.

---

## 1. Executive summary

PaperForge has a strong architecture once a paper instance is running:

- deterministic LaTeX-to-PreTeXt conversion;
- stable statement identities and numbering crosswalks;
- Lean declaration links and axiom/citation checks;
- an author-facing review/editing interface;
- configurable HTML enhancements;
- objective validators separated from generative agent skills;
- optional site, blueprint, and provenance pipelines.

The weak point is **bootstrapping a new instance**. The documented path from an empty repository to the first successful build is not currently closed. It relies on an agent to perform deterministic setup, omits prerequisite artifacts that the generated build script assumes already exist, duplicates configuration into generated shell and XSL files, contains some G\(_{\mathbf Q_2}\)-specific behavior, and is not portable to a standard GNU/Linux environment.

The goal of the work described here is:

> A user with a PaperForge checkout, a LaTeX draft, and a Lean project should be able to initialize an instance, diagnose their environment, bootstrap the crosswalks, build the HTML paper, run the validators, and open the review UI using a small set of deterministic commands. The G\(_{\mathbf Q_2}\) project must remain easy to develop in parallel with PaperForge, without requiring an exact PaperForge commit pin after every tool change.

The recommended target interface is:

```bash
python3 -m pip install -e ../paperforge

paperforge init .
paperforge doctor
paperforge ingest --bootstrap
paperforge build web
paperforge check
paperforge review
```

The exact command names may change, but the responsibilities should not.

---

## 2. Important constraints

### 2.1 Keep the current G\(_{\mathbf Q_2}\) instance working

The first exercised instance is not just a demonstration; it is still driving PaperForge’s design. Do not introduce an onboarding abstraction that makes iteration across `paperforge` and `gq2-paper` cumbersome.

In particular:

- a change made in a local PaperForge checkout should be immediately testable from the local G\(_{\mathbf Q_2}\) instance;
- normal development should not require updating a lock file after every PaperForge commit;
- machine-specific paths should not need to be committed;
- the G\(_{\mathbf Q_2}\) instance may temporarily exercise features that are still being generalized;
- migration should be incremental: old scripts and configuration should keep working while the new CLI is introduced.

### 2.2 Do not require exact version pinning during active development

An exact commit lock is useful for a released or archived paper, but it is counterproductive while the tool and first instance are evolving together.

Separate these three concepts:

1. **Instance schema compatibility**  
   A small integer or semantic schema version that tells PaperForge whether it knows how to read an instance’s committed configuration and artifact layout. This should be checked routinely.

2. **Development checkout selection**  
   Which local PaperForge source tree is being executed. During active development this should normally be an editable install or an explicitly selected checkout, with no exact-commit enforcement.

3. **Release provenance or freezing**  
   An optional record of the exact PaperForge commit and dependency versions used to produce a release. This can be created deliberately when publishing or archiving.

The implementation should enforce schema compatibility, always report build provenance, and make exact locking optional.

### 2.3 Preserve the validator/skill distinction

PaperForge’s separation between deterministic validators and generative agent skills is one of its strongest design decisions. Extend that principle to onboarding:

- copying templates, validating configuration, resolving paths, creating empty sidecars, running the converter, and orchestrating builds belong in deterministic commands;
- reviewing ambiguous converter output, deciding notation senses, assessing declaration matches, adding bridging prose, writing summaries, and revising exposition remain agent or author tasks.

### 2.4 Avoid a disruptive rewrite

The repository already contains working scripts and modules. Prefer a thin orchestration layer over a wholesale rewrite.

A good implementation sequence is:

1. introduce shared configuration/path utilities;
2. wrap existing tools in a CLI;
3. make the existing shell scripts call the CLI or become compatibility wrappers;
4. migrate the G\(_{\mathbf Q_2}\) instance;
5. delete duplicated logic only after parity tests pass.

---

## 3. Current strengths to preserve

The following parts of the current design should survive the onboarding work.

### 3.1 The two-repository model

PaperForge is the reusable tool; each paper has its own instance repository. This is the right boundary. Keep paper content, author decisions, reference files, and formalization pointers out of the tool repository.

### 3.2 Stable identities rather than printed numbers

The use of LaTeX labels converted to stable `xml:id` values is essential. Printed numbering may drift, while links, directives, and formalization correspondence should remain attached to stable tags.

### 3.3 Deterministic generated source

The generated `source/` tree should continue to be reproducible. User-authored additions should remain in explicit sidecars such as `content/insertions/`, and edits to converted prose should continue to flow back to the LaTeX draft rather than silently diverging in generated PreTeXt.

### 3.4 Validator contracts

Validators should continue to:

- read configuration and artifacts;
- never mutate the instance;
- report all findings rather than stopping at the first one;
- distinguish warnings from errors;
- be callable both through a package command and as Python modules.

### 3.5 Skill contracts

Agent skills should continue to declare:

- inputs;
- outputs;
- gates;
- provenance requirements.

The new deterministic commands should make those contracts easier to follow, not replace the judgment-bearing parts.

---

## 4. Definition of done

The onboarding work is complete when all of the following are true.

### 4.1 Fresh-instance smoke test

Starting from:

- a fresh PaperForge checkout;
- a new empty Git repository;
- a small amsart-style LaTeX draft;
- a small Lean source tree;

a user can run the documented commands and reach a successful HTML build without manually creating undocumented JSON files or editing generated placeholders.

### 4.2 Helpful incomplete-state behavior

If a reviewed artifact is not yet available, the command should stop in a named state with an actionable message, for example:

```text
Bootstrap ingestion completed.

Created:
  crosswalk/numbering-current.json
  crosswalk/lean-decl-map.candidate.json

Review the candidate declaration map, then run:
  paperforge accept lean-decl-map
  paperforge build web
```

It should not fail with a raw `FileNotFoundError`.

### 4.3 Cross-platform behavior

At minimum, the smoke test passes on:

- current Ubuntu in GitHub Actions;
- macOS, either in GitHub Actions or through a documented local test.

No generated script may rely on BSD-only `sed -i ''`.

### 4.4 G\(_{\mathbf Q_2}\) parallel development

A developer can:

1. edit `paperforge`;
2. run the G\(_{\mathbf Q_2}\) build against that working tree immediately;
3. inspect the actual PaperForge commit and dirty state used;
4. do so without updating an exact lock after each commit.

### 4.5 No generic G\(_{\mathbf Q_2}\)-specific transformations

The generic converter must not:

- hardcode the document ID `gq2-paper`;
- unconditionally rewrite `\MarkedDem`;
- silently assume the G\(_{\mathbf Q_2}\) numbering setup without an explicit profile or verification step.

### 4.6 Configuration has one authoritative interpretation

All paths are resolved consistently relative to the instance root unless explicitly documented otherwise. A command invoked as

```bash
paperforge check /path/to/instance
```

behaves the same as:

```bash
cd /path/to/instance
paperforge check
```

### 4.7 Documentation is literal

Copying the quickstart commands into a clean test environment produces the documented result. The public troubleshooting path does not depend on maintainer-only handoff notes or local memory files.

---

## 5. Highest-priority defects in the current onboarding path

This section records the issues found in the review. Later sections turn them into implementation work packages.

---

### P0. The documented first-build cycle is not closed

#### Current behavior

The README and `docs/GETTING-STARTED.md` tell the user to scaffold an instance, add the draft/style/reference inputs, and run:

```bash
scripts/build-web.sh
```

The generated `templates/build-web.sh` always supplies:

```bash
--lean-map <project>=crosswalk/lean-decl-map.json
--notation-map notation/notation-map.json
```

The converter opens each supplied map. There is no general “missing means empty” behavior for those arguments.

The `paper-init` skill creates some directories and sidecars, but does not clearly create every file the build assumes, and it does not generate `crosswalk/lean-decl-map.json`.

Generating the Lean declaration map itself requires a current numbering map, which is produced by ingestion. Therefore a new instance naturally needs a two-pass bootstrap:

1. ingest without a Lean map;
2. write current numbering;
3. mine a candidate declaration map from the Lean project;
4. review the candidate;
5. ingest again with accepted links.

#### Required fix

Implement a deterministic bootstrap state machine.

At minimum:

- missing optional notation, bibliography-label, disambiguation, annotation, and insertion sidecars should be represented by valid empty files or omitted CLI arguments;
- bootstrap ingestion must not require a Lean declaration map;
- after current numbering exists, generate `crosswalk/lean-decl-map.candidate.json`;
- do not silently promote heuristic matches to accepted links;
- provide an explicit acceptance or copy step;
- subsequent builds should use the accepted map.

A lightweight artifact convention could be:

```text
crosswalk/lean-decl-map.candidate.json
crosswalk/lean-decl-map.json
crosswalk/lean-decl-map.review.json
```

The exact names are flexible, but candidate and accepted data must not be confused.

#### Acceptance tests

- `paperforge ingest --bootstrap` succeeds in a new instance with no declaration map.
- It creates `numbering-current.json`.
- If a Lean project is configured, it creates a candidate declaration map.
- `paperforge build web` gives a precise message when only the candidate exists.
- An empty Lean project produces an empty candidate map rather than crashing.
- A project that intentionally disables formalization linkage can build without any Lean map.

---

### P0. Initialization is agent-operated despite being deterministic

#### Current behavior

`skills/paper-init/SKILL.md` instructs an agent to:

- copy template trees;
- create directories;
- fill placeholders;
- write configuration;
- copy scripts;
- create skeleton sidecars;
- print next commands.

Most of this is deterministic filesystem work.

#### Why this is a problem

- initialization cannot be reliably regression-tested;
- different agents can create different layouts;
- omitted files become onboarding failures;
- it is unclear whether a choice is architectural or improvised;
- updating the scaffold requires updating prose instructions and trusting every agent to follow them precisely.

#### Required fix

Implement `paperforge init` as a deterministic command. The agent skill should become a wrapper around it.

Suggested behavior:

```bash
paperforge init PATH [options]
```

The command should:

1. verify that `PATH` is empty or contains only a Git directory, unless `--force` is supplied;
2. copy the scaffold;
3. create all required empty sidecars with valid syntax;
4. create a conservative `.gitignore`;
5. write a minimal valid `paper.toml`;
6. write or preserve a machine-local configuration file;
7. leave no unresolved `@@PLACEHOLDER@@` strings;
8. run structural self-checks;
9. print the next commands.

The command may ask a few explicit questions in interactive mode, but it must also support noninteractive flags for tests.

Suggested flags:

```text
--title
--slug
--draft
--lean-root
--lean-project-name
--docs-root
--pretext-core-xsl
--detail-default
--detail-max
--non-interactive
```

Do not require all optional subsystems at initialization.

#### Skill update

Rewrite `skills/paper-init/SKILL.md` so that it says approximately:

1. run `paperforge init`;
2. inspect its report;
3. help the author make subjective or project-specific choices;
4. run `paperforge doctor`;
5. do not manually copy or edit generated scaffold files unless fixing the initializer itself.

---

### P0. The configuration model contains hidden and duplicated values

#### Current behavior

The template config has:

```toml
[inputs]
lean_project = ...
lean_docs_base = ...
```

but the initializer also needs values corresponding to:

- `@@LEAN_PROJECT_NAME@@`;
- `@@MATHBB_LETTERS@@`;
- a document ID;
- the relationship between the documentation root and named projects.

These values are not all represented clearly in `paper.toml`.

The current scaffold also stamps values into:

- shell scripts;
- HTML XSL;
- print XSL;
- arXiv XSL.

Changing the config later may not update all stamped copies.

#### Required fix

Introduce a normalized configuration schema and shared loader.

A suggested direction is:

```toml
[paper]
title = "Title of the paper"
slug = "my-paper"
document_id = "my-paper"

[inputs]
ai_draft = "inputs/draft/main.tex"

[formalizations.primary]
name = "my-lean-project"
root = "../my-lean-project"
module = "MyProject"
docs_root = "../lean/"
declmap = "crosswalk/lean-decl-map.json"

[style]
corpus = "style-corpus/"
advice = "style-corpus/ADVICE.md"

[references]
pdf_dir = "references/"
bib = "source/references.ptx"

[ingest]
numbering_profile = "amsart-section-theorems-global-equations"
mathbb_letters = ""

[detail]
default_level = 1
max_level = 3

[build]
web_output = "output/web"
print_output = "output/print"
```

Additional formalizations should use the same record shape:

```toml
[formalizations.secondary]
name = "other-model"
root = "formalizations/other-model"
module = "OtherModel"
docs_root = "../lean/"
declmap = "crosswalk/lean-decl-map-other.json"
badge_cap = 1
```

Backward compatibility is important. The loader should initially accept the existing `[inputs] lean_project`, `lean_docs_base`, and `[inputs.formalizations.*]` structure, normalize it internally, and emit deprecation warnings.

#### Configuration layering

Use three layers:

1. **Committed instance config:** `paper.toml`
2. **Optional gitignored machine-local config:** `.paperforge.local.toml`
3. **Environment/CLI overrides**

Suggested local-only values:

```toml
[build]
pretext_core_xsl = "/Users/name/.ptx/2.43.2/core/xsl/pretext-html.xsl"

[development]
paperforge_checkout = "../paperforge"
python = "/path/to/venv/bin/python3"
```

Do not commit author-machine paths in the generic template.

#### Shared path semantics

Implement a utility such as:

```python
resolve_instance_path(config, value) -> Path
```

Rules:

- relative paths in committed config are relative to the instance root;
- machine-local config follows the same rule unless documented otherwise;
- `~` may be expanded;
- environment variables should not be expanded silently unless explicitly supported;
- URLs must not pass through filesystem path resolution;
- every module must use the same helper.

This fixes the current discrepancy in which `paperforge-check /path/to/instance` can interpret relative Lean roots relative to the caller’s working directory.

---

### P0. There is no deterministic environment diagnosis

#### Current behavior

The getting-started guide lists dependencies and commands for checking them, but users must run and interpret them manually.

#### Required fix

Implement:

```bash
paperforge doctor [INSTANCE]
```

It should check:

- Python version;
- importability and versions of `lxml`, `yaml`, and any other required Python packages;
- that the `paperforge` package resolves to the expected checkout;
- the PaperForge Git commit and whether the checkout is dirty;
- `pretext --version`;
- supported PreTeXt version range;
- location and existence of core HTML/LaTeX XSL files;
- `latexmk`;
- a TeX engine;
- `pdftotext`;
- `xsltproc`;
- `xmllint`;
- optional Node/npm;
- optional `rsvg-convert`;
- optional PyMuPDF;
- existence and readability of the draft;
- existence of each formalization root;
- configuration schema validity;
- unresolved template placeholders;
- required directory and sidecar structure;
- whether the current state is uninitialized, scaffolded, bootstrapped, or buildable;
- whether machine-local configuration contains absolute paths that do not exist.

Output should be grouped and actionable:

```text
PaperForge doctor

OK      Python 3.13.5
OK      paperforge checkout: ../paperforge
INFO    checkout commit: abc1234 (dirty)
OK      PreTeXt 2.43.2
ERROR   core XSL not found:
        /Users/.../pretext-html.xsl
        Set build.pretext_core_xsl in .paperforge.local.toml
WARN    pdftotext not found; citation-pin verification will be skipped

State: scaffolded, not bootstrapped
Next: paperforge ingest --bootstrap
```

Exit status:

- `0`: no blocking errors;
- `1`: blocking configuration/environment problem;
- optionally `2`: command misuse.

---

### P1. The build wrapper is not portable

#### Current behavior

`templates/build-web.sh` contains BSD/macOS-specific commands:

```bash
sed -i '' ...
```

GNU `sed` treats this differently and fails.

The script also interpolates an unquoted PaperForge root into command paths.

#### Required fix

Move post-build mutations into Python functions or commands. Do not add a growing shell portability layer.

For example:

```bash
paperforge postprocess web
```

or internal Python functions invoked by `paperforge build web` should:

- add MathJax lazy loading;
- open the table of contents by default;
- generate the MathJax macro registry;
- generate notation and section-summary registries;
- concatenate UI assets;
- copy assets.

Each transformation should:

- detect whether the expected source pattern exists;
- fail or warn explicitly if upstream PreTeXt output has changed;
- be idempotent;
- have a focused test fixture.

The compatibility shell script can eventually become:

```bash
#!/usr/bin/env bash
set -euo pipefail
exec python3 -m paperforge build web "$@"
```

Use `python3 -m pip`, not bare `pip`, in documentation.

#### Acceptance tests

- a checkout path containing spaces works;
- Ubuntu smoke build passes;
- macOS smoke build passes;
- running postprocessing twice does not further change output;
- changed upstream MathJax startup content produces a clear compatibility error rather than silently shipping unpatched output.

---

### P1. Generic code still contains G\(_{\mathbf Q_2}\)-specific behavior

#### Hardcoded document ID

The converter currently writes:

```xml
<document-id>gq2-paper</document-id>
```

This must come from configuration or a command argument.

#### Unconditional `\MarkedDem` rewrite

The converter contains an unconditional rewrite of `\MarkedDem` to a specific cross-reference. Remove it from generic code.

A reasonable replacement is a configured deterministic preprocessing mechanism. Prefer a constrained, auditable format rather than arbitrary evaluation.

For example:

```toml
[[ingest.literal_rewrites]]
from = "\\MarkedDem"
to = "\\cref{prop:markedDem}"
```

The G\(_{\mathbf Q_2}\) instance can carry this rule. The converter should log applied rewrites.

If more complex preprocessing is eventually required, allow an instance-owned script only through an explicit opt-in such as:

```toml
[ingest]
preprocessor = "scripts/preprocess-tex.py"
```

and record the script hash in build provenance.

#### Numbering assumptions

The current numbering simulator is tuned to:

- section-numbered theorem-like environments sharing one counter;
- theorem counter reset by section;
- global equation numbering;
- specific appendix behavior.

Do not pretend this is universal amsart behavior.

Introduce an explicit profile:

```toml
[ingest]
numbering_profile = "amsart-section-theorems-global-equations"
```

For the first implementation, it is acceptable to support only the existing profile, provided:

- the profile is named;
- unsupported or inconsistent conventions are reported;
- initial numbering verification against the draft’s `.aux` is a documented and preferably automated gate.

Add:

```bash
paperforge verify numbering
```

It should compile the draft in an isolated build directory, parse `.aux` labels, compare them with the simulator, and report exact mismatches.

Do not mark a numbering baseline trusted until verification succeeds, unless the author explicitly records a waiver.

---

### P1. The scaffold lacks basic repository hygiene

#### Required fix

The initializer should create a conservative `.gitignore`, based on what the exercised instance actually needs, including at least:

```gitignore
output/
.cache/
__pycache__/
*.egg-info/
vendor/
.DS_Store
._*
*~
logs/

# Local machine configuration
.paperforge.local.toml

# LaTeX intermediates
*.aux
*.log
*.out
*.synctex.gz
*.fls
*.fdb_latexmk
```

Be careful not to ignore committed source PDFs or reference provenance files unintentionally. If reference PDFs are intentionally untracked, make that choice explicit in the template and documentation.

Also create all required empty files with valid formats, for example:

```text
notation/notation-map.json            {}
notation/disambiguation.json          {}
references/bib-labels.json            {}
references/bib-aliases.json           {}
crosswalk/lean-annotations.json        {"annotations": {}}
references/extra-biblio.xml            a valid empty fragment root or documented fragment format
content/authors.xml                    valid scaffold with no active records
```

The exact empty shapes must match what the consumers expect.

---

### P1. “Source of truth” language is contradictory

#### Current behavior

The README says PreTeXt is the source of truth, while the getting-started guide says `source/` is generated, must never be hand-edited, and that edits flow back into the LaTeX draft.

#### Required fix

Use precise terminology.

Recommended wording:

> The canonical editable inputs are the LaTeX draft plus committed PaperForge sidecars: insertions, author metadata, notation decisions, directives, and configuration. PaperForge deterministically assembles these into a canonical PreTeXt intermediate representation, from which HTML and LaTeX/PDF outputs are generated.

Then answer the practical question directly:

> To change existing prose, edit the draft through the paper editor or directly in LaTeX. To add persistent PaperForge-only material, use `content/insertions/`. Do not hand-edit `source/`.

If the long-term intent is truly to make PreTeXt independently editable, that would require a different synchronization model. Do not claim that model before it exists.

---

### P1. Public troubleshooting points to maintainer-only state

#### Current behavior

The getting-started guide refers readers to `HANDOFF`, which includes machine-specific paths, mutable session state, and directions to read local memory not present in the repository.

#### Required fix

Create `docs/TROUBLESHOOTING.md` containing stable, public guidance:

- interpreter mismatch;
- locating PreTeXt XSL files;
- first-build states;
- converter warnings;
- numbering mismatches;
- missing or stale declaration maps;
- drift-gate failures;
- HTML enhancement failures;
- review-server write safety;
- cache-busting and browser verification;
- missing optional dependencies;
- how to collect a diagnostic bundle.

Keep `HANDOFF` as maintainer memory if useful, but do not use it as public documentation.

Consider:

```bash
paperforge diagnostics --output paperforge-diagnostics.zip
```

which collects versions, config with secrets/paths redacted where appropriate, logs, and state summaries, but not paper content unless explicitly requested.

---

### P1. There is no minimal public reproducible instance

#### Required fix

Add a fixture or example instance under a path such as:

```text
examples/minimal-paper/
```

or as a separate public repository if keeping instances out of the tool tree is important. For CI convenience, an in-repository fixture is reasonable even if it is not presented as a real paper.

It should contain:

- a short amsart draft;
- an abstract;
- two sections;
- a theorem, lemma, definition, remark, and proof;
- labeled and unlabeled equations;
- one bibliography entry and citation;
- one notation definition and later use;
- one persistent insertion;
- a tiny Lean tree with declaration names/docstrings exercising the mapper;
- expected current numbering;
- expected declaration-map candidate;
- expected assembled PreTeXt;
- no copyrighted reference PDFs.

The fixture should be intentionally small enough that a failure is easy to inspect.

---

## 6. Target command design

The following interface is recommended. It is fine to implement a subset first, but avoid creating commands whose responsibilities will later overlap confusingly.

---

### 6.1 `paperforge init`

```bash
paperforge init [INSTANCE]
```

Responsibilities:

- deterministic scaffolding;
- minimal config creation;
- local-config creation or instructions;
- sidecar creation;
- `.gitignore`;
- placeholder elimination;
- initial state report.

It should not:

- generate substantive prose;
- accept heuristic Lean mappings as reviewed;
- build the entire site;
- require optional deployment or provenance settings.

---

### 6.2 `paperforge doctor`

```bash
paperforge doctor [INSTANCE]
```

Responsibilities:

- environment checks;
- config validation;
- path normalization;
- schema compatibility;
- current state detection;
- actionable next command.

---

### 6.3 `paperforge ingest`

```bash
paperforge ingest [INSTANCE]
paperforge ingest --bootstrap [INSTANCE]
```

Normal mode:

- ingest using accepted sidecars and declaration maps;
- write generated PreTeXt and numbering;
- write source map;
- report warnings;
- validate XML;
- check idempotency when requested.

Bootstrap mode:

- tolerate absent accepted declaration map;
- produce current numbering;
- generate candidates;
- create worklists;
- stop at review boundaries.

Useful flags:

```text
--bootstrap
--verify-numbering
--no-lean
--formalization NAME
--check-idempotent
--snapshot NAME
```

---

### 6.4 `paperforge build`

```bash
paperforge build web [INSTANCE]
paperforge build arxiv [INSTANCE]
paperforge build site [INSTANCE]
paperforge build all [INSTANCE]
```

Responsibilities:

- orchestrate deterministic steps in the correct order;
- respect optional configuration;
- call existing generators;
- run postprocessing portably;
- report skipped optional stages;
- write build provenance;
- avoid hidden mutation outside declared generated artifacts.

It should not silently accept unreviewed candidate maps.

---

### 6.5 `paperforge check`

```bash
paperforge check [INSTANCE]
```

This should invoke the existing validator suite. Keep `paperforge-check` as a compatibility entry point.

Add a shared path/config layer so every validator sees the same normalized configuration.

Potential flags:

```text
--format text
--format json
--only lean_links,references
--no-warnings
```

JSON output would help agents and CI but is not essential for the first pass.

---

### 6.6 `paperforge review`

```bash
paperforge review [INSTANCE]
```

Responsibilities:

- verify the web build exists;
- start one review server rooted at the instance;
- print URL and process safety warning;
- optionally detect an existing server lock;
- use atomic writes as the current server does.

A lock/PID file can prevent accidental second writers:

```text
.cache/paperforge/review-server.pid
```

Do not rely solely on it for correctness; keep atomic writes and in-process locking.

---

### 6.7 `paperforge verify`

Suggested subcommands:

```bash
paperforge verify numbering
paperforge verify scaffold
paperforge verify idempotency
```

These can initially be internal helpers called by `doctor` or `ingest`.

---

## 7. Package and module structure

A root package would simplify installation and eliminate path-stamped script calls.

Suggested layout:

```text
paperforge/
  __init__.py
  __main__.py
  cli.py
  config.py
  paths.py
  state.py
  provenance.py
  commands/
    init.py
    doctor.py
    ingest.py
    build.py
    check.py
    review.py
    verify.py
  postprocess/
    mathjax.py
    toc.py
    assets.py
```

The existing directories can remain:

```text
ingest/
validators/
review/
sitegen/
records/
skills/
templates/
pretext-template/
```

The new package should call into them rather than duplicate their logic.

A root `pyproject.toml` could expose:

```toml
[project.scripts]
paperforge = "paperforge.cli:main"
paperforge-check = "paperforge.commands.check:main"
```

The existing `validators/pyproject.toml` may remain temporarily, but the long-term user installation should be one command from the repository root.

Use the standard library `argparse` unless a CLI framework provides a concrete benefit. Avoid adding a large dependency for a small command surface.

---

## 8. Configuration migration and compatibility

### 8.1 Add an explicit instance schema

Add to committed config:

```toml
[paperforge]
instance_schema = 1
```

The tool should expose a supported schema range.

Behavior:

- supported schema: continue;
- older migratable schema: warn and offer `paperforge migrate`;
- newer schema: fail clearly because the running tool may not understand the instance.

This is the routine compatibility mechanism. It should not depend on an exact Git commit.

### 8.2 Normalize old and new config internally

Create dataclasses or typed structures such as:

```python
@dataclass(frozen=True)
class FormalizationConfig:
    name: str
    root: Path
    module: str | None
    docs_root: str | None
    declmap: Path
    badge_cap: int | None

@dataclass(frozen=True)
class InstanceConfig:
    root: Path
    title: str
    slug: str
    document_id: str
    draft: Path
    formalizations: tuple[FormalizationConfig, ...]
    ...
```

The rest of PaperForge should consume these normalized objects rather than raw nested dictionaries.

For the transition:

- load old keys;
- map them to the normalized form;
- emit one deprecation warning per old key family;
- provide `paperforge migrate config --check` and `--write`.

### 8.3 Avoid regenerating scripts just to change config

The preferred end state is that instance scripts contain no embedded project values. They should invoke the installed command.

For compatibility, existing stamped scripts can continue to work until the G\(_{\mathbf Q_2}\) migration is complete.

### 8.4 Keep URLs and paths distinct

The current documentation naming around `lean_docs_base` is ambiguous. Use distinct names:

- `docs_root`: URL or relative deployed URL prefix;
- `root`: local filesystem path to the formalization;
- `declmap`: local filesystem path;
- `name`: project key used in badge classes and deployed docs subdirectories.

Validate URL-like values separately from paths.

---

## 9. Version tracking and parallel development design

This section is intentionally more detailed because exact version pinning is the one recommendation that should **not** be imposed rigidly during current development.

### 9.1 Design goals

The design must support both:

#### Active paired development

- PaperForge and `gq2-paper` are edited concurrently.
- The instance uses the current local PaperForge working tree.
- Dirty tool changes may be deliberately tested.
- Builds should identify the actual tool state but not refuse to run.

#### Reproducible release

- A published paper/site can record the exact tool commit and important dependency versions.
- Another machine can detect that it is building with a different tool state.
- Exact enforcement is opt-in.

### 9.2 Recommended model

#### A. Hard compatibility is schema-based

Committed in `paper.toml`:

```toml
[paperforge]
instance_schema = 1
```

This is always checked.

#### B. Development uses an editable install

Recommended local setup:

```bash
python3 -m venv ../paperforge-venv
source ../paperforge-venv/bin/activate
python3 -m pip install -e ../paperforge
```

Because the installation is editable, changes in the PaperForge checkout are immediately visible from `gq2-paper`.

The instance should call:

```bash
python3 -m paperforge build web
```

or the `paperforge` console script, not a copied absolute `$PF/...` path.

`paperforge doctor` should print the resolved package source directory, commit, and dirty state so the developer can verify which checkout is active.

#### C. Machine-local checkout selection is not committed

When an editable install is not enough, support one of:

```text
PAPERFORGE_ROOT=/path/to/paperforge
```

or `.paperforge.local.toml`:

```toml
[development]
paperforge_checkout = "../paperforge"
```

The local override should be gitignored.

Do not put `/Users/roed/...` paths into the committed template.

#### D. Every build records provenance, but development builds do not enforce it

Write a generated file such as:

```text
output/build-provenance.json
```

with:

```json
{
  "paperforge": {
    "repository": "roed-math/paperforge",
    "commit": "abc123...",
    "dirty": true,
    "source": "/absolute/path/for-local-diagnostics-only"
  },
  "instance": {
    "commit": "def456...",
    "dirty": false,
    "schema": 1
  },
  "pretext": {
    "version": "2.43.2"
  },
  "python": "3.13.5",
  "generated_utc": "..."
}
```

Do not commit absolute local paths into public provenance. The release-copy step should redact or omit `source`.

Development builds may be dirty. Report this visibly:

```text
Built with paperforge abc1234+dirty
```

but do not fail.

#### E. Exact freezing is optional

Provide later, or in the first implementation if straightforward:

```bash
paperforge freeze
paperforge thaw
paperforge verify lock
```

`paperforge freeze` creates a committed `paperforge.lock`:

```toml
lock_format = 1

[paperforge]
repository = "https://github.com/roed-math/paperforge"
commit = "abc123..."
instance_schema = 1

[dependencies]
pretext = "2.43.2"
python = "3.13"
```

When a lock exists:

- normal builds warn on mismatch by default;
- `paperforge build --locked` or a release command fails on mismatch;
- `paperforge thaw` removes or disables the lock for active development.

Do **not** create a mandatory lock during `paperforge init`.

For the current G\(_{\mathbf Q_2}\) workflow, leave the instance unfrozen while PaperForge is evolving. Freeze only a release snapshot or archival tag.

### 9.3 Suggested G\(_{\mathbf Q_2}\) development loop

From a shared virtual environment:

```bash
# Once
python3 -m pip install -e ~/claude/paperforge

# Repeatedly
cd ~/claude/paperforge
# edit and test tool

cd ~/claude/gq2-paper
paperforge doctor
paperforge build web
paperforge check
```

`doctor` should show:

```text
paperforge source: /Users/roed/claude/paperforge
paperforge commit: abc1234 (dirty)
instance schema: 1 (supported)
version lock: none (development mode)
```

This gives transparency without friction.

### 9.4 Optional worktree support

The design should also work with Git worktrees. A developer may want:

```text
paperforge/
paperforge-feature/
gq2-paper/
```

and install `paperforge-feature` editable into a dedicated virtual environment. No instance file should assume the checkout’s directory name or branch.

### 9.5 What not to do

Do not:

- make the G\(_{\mathbf Q_2}\) instance update an exact commit in `paper.toml` after every PaperForge commit;
- make the tool a Git submodule of every active instance as the only supported development mode;
- use a mutable path as though it were a version pin;
- hide the fact that a dirty PaperForge checkout produced a build;
- conflate PreTeXt compatibility with PaperForge Git identity.

---

## 10. Bootstrap state model

A small explicit state model will simplify commands and error messages.

Suggested states:

1. **uninitialized**  
   No valid `paper.toml`.

2. **scaffolded**  
   Config and scaffold exist; draft or dependencies may be missing.

3. **ready-to-bootstrap**  
   Required environment and draft exist.

4. **bootstrapped-unreviewed**  
   Current numbering and candidate maps/worklists exist, but judgment artifacts are not accepted.

5. **buildable**  
   Required accepted artifacts exist.

6. **built-web**  
   Web output is current enough to serve.

7. **validated**  
   Validators last ran successfully against the current generated artifacts.

Do not store a single authoritative state flag that can drift. Derive state from artifacts and hashes. A small status command may explain the derivation:

```bash
paperforge status
```

Example:

```text
State: bootstrapped-unreviewed

Present:
  numbering-current.json
  lean-decl-map.candidate.json

Missing:
  lean-decl-map.json

Next:
  review crosswalk/lean-decl-map.candidate.json
  paperforge accept lean-decl-map
```

Hashes or source metadata should let the tool tell whether a candidate was generated from the current draft and Lean commit.

---

## 11. Candidate-artifact review design

The current system relies on an agent for some heuristic outputs. Make those review boundaries explicit.

### 11.1 Lean declaration map

`lean_declmap.py` uses naming and docstring heuristics. Its own documentation says the output must be reviewed. Preserve that.

Candidate entries should include enough evidence:

```json
{
  "thm-main": [
    {
      "decl": "MyProject.mainTheorem",
      "via": "docstring",
      "cited": "theorem 1.2",
      "file": "MyProject/Main.lean",
      "line": 42,
      "kind": "theorem",
      "flagged": true,
      "confidence": "high"
    }
  ]
}
```

Acceptance can be a simple copy initially, but it should be deliberate. A later review UI can support item-level acceptance.

### 11.2 Notation disambiguation

Missing or ambiguous notation decisions should produce worklists without blocking the bootstrap conversion. They may block the enhanced final build if the project requires full notation coverage.

### 11.3 Bibliography labels and aliases

Safe empty defaults should exist. Missing labels may produce warnings and serial labels; missing axiom aliases should produce targeted worklists.

### 11.4 Provenance

Accepted or modified candidate artifacts should retain:

- generator/tool version;
- source hashes or commits;
- review status;
- reviewer or agent identifier where available.

Do not put volatile timestamps into artifacts whose deterministic content is expected to remain byte-identical unless the project has already chosen that convention.

---

## 12. Build orchestration details

The new build command should encode the existing required order rather than relying on comments in copied shell scripts.

A web build currently needs roughly:

1. trust-table generation, if configured;
2. LaTeX ingestion;
3. author metadata application;
4. axiom census generation, if formalization configured;
5. trust-table drift check, if configured;
6. notation far-use marking;
7. prose-term wrapping, if configured;
8. PreTeXt HTML build;
9. robust HTML/MathJax postprocessing;
10. notation registry;
11. section-summary registry;
12. UI bundle assembly;
13. asset copy;
14. build provenance.

Represent stages as Python functions with names and logs.

Suggested output:

```text
[1/12] trust table                 skipped (not configured)
[2/12] ingest draft               OK
[3/12] author metadata            skipped (no active records)
[4/12] axiom census               OK (12 classical interfaces)
[5/12] trust drift                OK
...
[12/12] provenance                OK

Web build complete: output/web
```

A stage should be skipped only for a documented reason. “File missing” and “feature not configured” must not be conflated.

### 12.1 Build plans

A useful dry run:

```bash
paperforge build web --plan
```

could print enabled/skipped stages and resolved inputs without changing files. This is especially helpful while config is evolving.

### 12.2 Currentness and drift

Generated artifacts should record enough source identity for `doctor`, `status`, or validators to say:

- declaration map generated from old Lean commit;
- numbering baseline generated from old draft hash;
- web output older than generated source;
- registry older than source.

Avoid relying solely on mtimes for committed artifacts.

---

## 13. Portability and filesystem safety

### 13.1 Shell minimization

Keep shell only for tiny compatibility entry points. Use Python for:

- text replacement;
- path handling;
- file copying;
- recursive asset assembly;
- platform detection;
- temporary directories;
- atomic writes.

### 13.2 Atomic writes

The review server already uses temporary files plus `os.replace`. Extend this principle to generated JSON and config migrations where partial writes would be harmful.

### 13.3 Quoting and spaces

Add a smoke test whose instance path contains spaces, for example:

```text
/tmp/paperforge test/minimal paper
```

Every command should work there.

### 13.4 Symlinks

Decide and document how symlinks are handled when copying:

- reference directories;
- formalization roots;
- site assets.

Do not dereference unexpectedly during initialization.

### 13.5 Windows

Native Windows support need not be a first-pass goal if PreTeXt/TeX assumptions make it costly. State the supported platforms rather than accidentally implying portability. WSL support may follow from Ubuntu support.

---

## 14. Tests and CI

### 14.1 Unit tests

Add focused tests for:

- config normalization;
- old-schema compatibility;
- local override merging;
- relative path resolution;
- URL/path distinction;
- initialization into an empty repository;
- refusal to overwrite;
- empty sidecar shapes;
- placeholder detection;
- bootstrap with no Lean map;
- candidate versus accepted map handling;
- document ID configuration;
- configured literal rewrites;
- removal of unconditional `\MarkedDem` behavior;
- numbering profile selection;
- build provenance generation;
- dirty Git checkout detection;
- postprocessing idempotency;
- validator invocation with an instance path outside the current directory.

### 14.2 Minimal integration fixture

Use the minimal example described above. Tests should verify:

- deterministic scaffold;
- deterministic ingestion;
- XML validity;
- expected numbering;
- expected candidate map;
- accepted map produces badges;
- missing optional features skip cleanly;
- validators report expected findings;
- web build output contains expected UI assets.

### 14.3 CI matrix

Suggested GitHub Actions jobs:

#### Python-only

Matrix over supported Python versions, running unit tests without PreTeXt/TeX.

#### Ubuntu integration

Install:

- PreTeXt pinned to the exercised version;
- TeX dependencies sufficient for the fixture;
- `libxml2-utils`;
- `xsltproc`;
- Poppler.

Run the literal quickstart against the minimal fixture.

#### macOS integration

At least run:

- initialization;
- doctor;
- bootstrap;
- postprocessing tests.

A complete PreTeXt build is preferable if setup time is acceptable.

### 14.4 Regression test against G\(_{\mathbf Q_2}\)

Because the real instance is private, the public repository cannot run a full CI build against it. Maintain a local parity script or test protocol:

```bash
paperforge migrate config --check
paperforge build web
paperforge check
git diff --exit-code -- source crosswalk web-assets ...
```

For generalized components that were previously byte-compared with G\(_{\mathbf Q_2}\), keep fixture snapshots in PaperForge so regressions do not depend only on private local testing.

---

## 15. Documentation rewrite

### 15.1 README

The README should remain a conceptual front door, but the quickstart should be literal and short.

Suggested shape:

```bash
git clone https://github.com/roed-math/paperforge
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e paperforge

mkdir my-paper && cd my-paper && git init
paperforge init .
# edit paper.toml and .paperforge.local.toml, add the draft
paperforge doctor
paperforge ingest --bootstrap
paperforge build web
paperforge check
paperforge review
```

Link to the detailed guide for:

- review of candidate mappings;
- optional site/deployment;
- multiple formalizations;
- records pipelines.

### 15.2 `docs/GETTING-STARTED.md`

Organize by milestones:

1. install PaperForge;
2. create an instance;
3. configure machine-local dependencies;
4. run doctor;
5. bootstrap;
6. review candidate artifacts;
7. first web build;
8. validators;
9. review/edit loop;
10. PDF;
11. optional site.

Include exact expected output at key transitions.

### 15.3 `docs/TROUBLESHOOTING.md`

Create this as described earlier and remove public reliance on `HANDOFF`.

### 15.4 `docs/CONFIGURATION.md`

The config is becoming important enough to deserve its own reference. Document:

- every key;
- whether committed or local;
- default;
- path base;
- optionality;
- deprecation aliases;
- examples for zero, one, and two formalizations.

### 15.5 `docs/DEVELOPMENT.md`

Document paired PaperForge/G\(_{\mathbf Q_2}\) development:

- editable installation;
- checking resolved checkout;
- dirty-build provenance;
- optional freeze;
- worktrees;
- local parity procedure.

### 15.6 Agent skills

Update all skills that invoke raw scripts or assume stamped paths. They should invoke deterministic commands and focus on judgment work.

In particular:

- `paper-init`;
- `ingest-draft`;
- `update-formalization`;
- any deployment or review skill.

---

## 16. Migration plan for `gq2-paper`

Do not migrate the private instance in one opaque step. Use a parity-oriented sequence.

### Step 1: Introduce the CLI without changing G\(_{\mathbf Q_2}\)

- Add package and commands.
- Keep old scripts functional.
- Test CLI on the minimal fixture.

### Step 2: Make G\(_{\mathbf Q_2}\) call the editable PaperForge package

Replace direct `$PF/ingest/...` calls gradually with CLI stages or a single build command.

During transition, allow a command such as:

```bash
paperforge build web --legacy-compatible
```

only if genuinely needed. Avoid permanent compatibility flags.

### Step 3: Migrate config through normalization

First make the new loader accept the current config unchanged. Then generate a proposed migrated config:

```bash
paperforge migrate config --output paper.toml.new
```

Review the diff before replacing the file.

### Step 4: Move machine-local paths out of committed config

Move the PreTeXt XSL absolute path and any local checkout path to `.paperforge.local.toml`.

### Step 5: Move G\(_{\mathbf Q_2}\)-specific rewrite into the instance

Add its literal rewrite or preprocessor configuration to the instance. Confirm byte parity.

### Step 6: Parameterize the document ID

Set `document_id = "gq2-paper"` in the instance and remove the hardcode.

### Step 7: Replace shell postprocessing

Run old and new web builds and byte-compare relevant output, allowing only documented provenance differences.

### Step 8: Add development provenance

Confirm that builds made from a dirty PaperForge checkout are marked but not blocked.

### Step 9: Optional release freeze

Do not freeze during normal paired development. Test `paperforge freeze` on a release branch or tag when useful.

---

## 17. Suggested commit sequence

Keep changes reviewable. A possible sequence is:

1. **Add tests for current onboarding failures**  
   Missing maps, relative path bug, hardcoded document ID, `\MarkedDem`, GNU postprocessing failure.

2. **Add shared config and path normalization**  
   No user-facing CLI yet; adapt validators first.

3. **Add root package and `paperforge doctor`**  
   Include source-checkout and schema reporting.

4. **Add deterministic `paperforge init`**  
   Scaffold, sidecars, `.gitignore`, no placeholders.

5. **Add bootstrap ingestion**  
   Map-free first pass and candidate declaration maps.

6. **Add `paperforge build web` orchestration**  
   Initially call existing tools.

7. **Replace shell postprocessing with Python**  
   Add portability/idempotency tests.

8. **Parameterize document ID and preprocessing**  
   Remove G\(_{\mathbf Q_2}\) leaks.

9. **Add numbering profile and verification command**  
   Keep existing profile as the first supported profile.

10. **Add provenance and schema compatibility**  
    Development-friendly, no mandatory exact lock.

11. **Add minimal example and CI smoke jobs**

12. **Rewrite onboarding and troubleshooting docs**

13. **Migrate G\(_{\mathbf Q_2}\) locally with parity checks**

Avoid combining the CLI, schema migration, converter rewrite, and G\(_{\mathbf Q_2}\) migration into one giant commit.

---

## 18. Detailed acceptance checklist

A local agent should not consider the project complete until this checklist is satisfied.

### Initialization

- [ ] `paperforge init` works noninteractively.
- [ ] It refuses to overwrite an existing paper unless explicitly allowed.
- [ ] It creates all required directories and valid empty sidecars.
- [ ] It creates `.gitignore`.
- [ ] It leaves no `@@PLACEHOLDER@@` markers.
- [ ] It writes an explicit instance schema.
- [ ] It does not write `/Users/roed/...` defaults.
- [ ] Running it twice does not silently overwrite user content.

### Doctor

- [ ] Reports the actual imported PaperForge checkout.
- [ ] Reports Git commit and dirty state.
- [ ] Checks PreTeXt version and XSL paths.
- [ ] Checks required and optional executables separately.
- [ ] Validates normalized config.
- [ ] Resolves relative paths against the instance root.
- [ ] Identifies the current bootstrap/build state.
- [ ] Prints one clear next command.

### Bootstrap

- [ ] Succeeds without an accepted Lean map.
- [ ] Produces current numbering.
- [ ] Produces a candidate map when Lean is configured.
- [ ] Does not silently treat the candidate as accepted.
- [ ] Tolerates intentionally disabled formalization linkage.
- [ ] Creates worklists for ambiguous notation rather than crashing.
- [ ] Can verify numbering against `.aux`.

### Build

- [ ] Works on Ubuntu.
- [ ] Works on macOS.
- [ ] Works from a path containing spaces.
- [ ] Uses no BSD-only `sed`.
- [ ] Skips optional stages only when unconfigured.
- [ ] Distinguishes unconfigured from missing required files.
- [ ] Postprocessing is idempotent.
- [ ] Writes build provenance.
- [ ] Dirty PaperForge checkout is reported but allowed in development.
- [ ] Existing `paperforge-check` remains usable.

### Genericity

- [ ] Document ID comes from config.
- [ ] No unconditional `\MarkedDem` rewrite remains.
- [ ] G\(_{\mathbf Q_2}\)-specific preprocessing lives in its instance.
- [ ] Numbering assumptions are named by profile.
- [ ] Unsupported numbering conventions are not silently accepted.
- [ ] Primary and additional formalizations share one normalized schema.

### Version/development behavior

- [ ] Instance schema compatibility is enforced.
- [ ] Exact Git commit matching is not required for an unlocked development instance.
- [ ] Editable install supports immediate PaperForge/G\(_{\mathbf Q_2}\) iteration.
- [ ] Build provenance captures commit and dirty state.
- [ ] Optional freeze/lock, if implemented, is opt-in.
- [ ] Machine-local checkout paths are gitignored.

### Documentation and CI

- [ ] Literal README quickstart passes in CI.
- [ ] Minimal public fixture exists.
- [ ] Public troubleshooting does not point to `HANDOFF`.
- [ ] Config keys and path semantics are documented.
- [ ] Parallel development workflow is documented.
- [ ] Old config migration is documented.

---

## 19. Non-goals for this round

Do not let these items delay fixing onboarding:

- supporting every LaTeX package or theorem-numbering convention;
- replacing PreTeXt;
- building a fully general plugin architecture;
- implementing native Windows support;
- converting every skill into an autonomous agent runner;
- redesigning the review UI;
- creating a public package release on PyPI;
- exact dependency reproducibility for every external tool;
- eliminating every shell script immediately;
- generalizing the records pipeline beyond what the second instance needs.

The first objective is a reliable project number two.

---

## 20. Guidance for the implementing agent

### 20.1 Start by reproducing failures

Before modifying behavior:

1. create a fresh temporary instance using the documented process;
2. record the exact first failure;
3. add a regression test;
4. test on GNU/Linux or a GNU userland, not only macOS.

### 20.2 Prefer source inspection over assumptions

Search all templates, skills, and docs for:

```text
@@
gq2
GQ2
/Users/roed
~/claude
PAPERFORGE_ROOT
lean_project
lean_docs_base
sed -i
HANDOFF
source of truth
```

Each occurrence should be classified as:

- intentionally generic documentation;
- instance-specific and should move;
- machine-specific and should become local config;
- stale compatibility behavior;
- acceptable exercised-example reference.

### 20.3 Preserve byte parity where intended

For transformations ported from shell to Python, compare output before and after on the G\(_{\mathbf Q_2}\) instance. Differences should be:

- absent; or
- limited to deliberately changed provenance strings and documented behavior.

### 20.4 Do not overfit the minimal fixture

The fixture should catch onboarding defects, but implementation decisions should continue to respect the real G\(_{\mathbf Q_2}\) complexity: multiple formalizations, private declarations, badge caps, old numbering snapshots, insertions, trust table, and author metadata.

### 20.5 Keep errors actionable

A good error names:

- the missing or invalid artifact;
- why it is required;
- which command generates it;
- whether the problem is configuration, environment, or review state.

Bad:

```text
FileNotFoundError: crosswalk/lean-decl-map.json
```

Good:

```text
No accepted Lean declaration map exists at:
  crosswalk/lean-decl-map.json

A candidate map was generated from formalization "primary":
  crosswalk/lean-decl-map.candidate.json

Review and accept it, or disable formalization badges for this build.
```

### 20.6 Keep deterministic commands non-generative

Do not make `paperforge init` or `paperforge build` call an LLM. They should produce worklists and stop where judgment is required.

---

## 21. File-level starting points

These are the main files likely to change.

### Front door and docs

- `README.md`
- `docs/GETTING-STARTED.md`
- new `docs/CONFIGURATION.md`
- new `docs/TROUBLESHOOTING.md`
- new `docs/DEVELOPMENT.md`
- `docs/ARCHITECTURE.md`

### Skills

- `skills/paper-init/SKILL.md`
- `skills/ingest-draft/SKILL.md`
- `skills/update-formalization/SKILL.md`
- other skills that invoke raw paths or copied scripts

### Templates and scaffold

- `templates/paper.toml`
- `templates/build-web.sh`
- `templates/build-site.sh`
- `templates/deploy.sh`
- `pretext-template/project.ptx`
- `pretext-template/source/main.ptx`
- `pretext-template/xsl/custom-html.xsl`
- `pretext-template/xsl/print-latex.xsl`
- `pretext-template/xsl/arxiv-latex.xsl`
- new scaffold `.gitignore`
- empty sidecar templates

### Converter and crosswalks

- `ingest/tex2ptx.py`
- `ingest/lean_declmap.py`
- `ingest/lean_axioms.py`
- notation/bibliography loaders that currently assume files exist

### Validators

- `validators/paperforge_validators/__init__.py`
- `validators/paperforge_validators/run_all.py`
- `validators/paperforge_validators/lean_links.py`
- `validators/paperforge_validators/numbering_drift.py`
- any validator that constructs paths directly from raw config

### Build and review

- new root `paperforge/` package
- `review/review_server.py`
- `sitegen/` modules called by the orchestrator

### Packaging

- new root `pyproject.toml`, or a deliberate consolidation plan
- compatibility handling for `validators/pyproject.toml`

### Tests/examples

- new `tests/`
- new `examples/minimal-paper/` or equivalent fixture
- `.github/workflows/...`

---

## 22. Proposed revised quickstart

This is the user experience the implementation should make true.

```bash
# Tool setup
git clone https://github.com/roed-math/paperforge
python3 -m venv paperforge/.venv
source paperforge/.venv/bin/activate
python3 -m pip install -e paperforge

# Instance setup
mkdir my-paper
cd my-paper
git init
paperforge init . \
  --title "My Paper" \
  --slug my-paper \
  --draft inputs/draft/main.tex \
  --lean-root ../my-paper-lean \
  --lean-project-name my-paper-lean

# Put the LaTeX draft at inputs/draft/main.tex, then:
paperforge doctor
paperforge ingest --bootstrap

# Review the generated candidate mappings/worklists.
# The exact acceptance command may differ:
paperforge accept lean-decl-map

paperforge build web
paperforge check
paperforge review
```

For an instance with no Lean formalization:

```bash
paperforge init . --no-lean
paperforge doctor
paperforge ingest --bootstrap
paperforge build web
paperforge check
```

The system should degrade gracefully rather than treating every feature of the first instance as mandatory.

---

## 23. Final assessment

PaperForge is already more than a prototype in its core capabilities. Its converter, validators, crosswalk machinery, review interface, and site tooling reflect substantial real-world exercise. The remaining obstacle to adoption is not a lack of features; it is the absence of a deterministic, tested front door.

The most important changes are:

1. replace agent-performed scaffolding with `paperforge init`;
2. add `paperforge doctor`;
3. make bootstrap ingestion a real supported state;
4. normalize configuration and paths;
5. replace platform-specific shell postprocessing;
6. move G\(_{\mathbf Q_2}\)-specific behavior into the instance;
7. add a minimal public fixture and literal quickstart CI;
8. track schema compatibility and build provenance without forcing exact commit locks during active paired development.

The version design should favor current reality: `paperforge` and `gq2-paper` are co-evolving. An editable installation plus explicit build provenance gives fast parallel development and transparency. Exact freezing should be available when a release needs it, but it should not be the default development constraint.


# Troubleshooting

Public, stable guidance — nothing here depends on maintainer handoff notes.
`paperforge doctor` should be your first move for anything
environment-shaped: it names the problem and the next command.

## Interpreter mismatch

Symptom: `ModuleNotFoundError: lxml` (or `tomllib`) from a build step that
"worked yesterday", or a subprocess dying on an import the parent could do.

The `python3` on `PATH` must be the one with the project's packages —
conda/homebrew/system splits are the classic cause. Fix: put the right
interpreter first in `PATH` for every session; tools that spawn
subprocesses already lead `PATH` with `sys.executable`'s directory.
`paperforge doctor` prints which interpreter it is running under.

## PreTeXt core XSL not found

The instance's conversions import machine-local shims
(`xsl/core-local/*.xsl`, gitignored). If the shims are missing or point at
a deleted install, `paperforge doctor` regenerates them — from
`[build] pretext_core_xsl` in `.paperforge.local.toml` when set, else by
discovery (`~/.ptx/*/core/xsl`, or the pretext wheel's on-demand
materialization). Older instances that committed an absolute core path in
their XSLs instead: update the path in the XSL, or switch to the shim
pattern.

## First-build states

`paperforge status` derives where you are from artifacts on disk:

- **scaffolded** — put the draft at `[inputs] ai_draft`.
- **ready-to-bootstrap** — `paperforge ingest --bootstrap`.
- **bootstrapped-unreviewed** — a candidate declaration map exists;
  review it, then `paperforge accept lean-decl-map`. Builds refuse to use
  an unaccepted candidate by design: the mining is heuristic.
- **buildable** — `paperforge build web`.

## Converter warnings and numbering mismatches

The numbering simulator implements one named profile
(`amsart-shared-section-theorems-global-equations`). If your draft's
theorem/equation conventions differ, tex2ptx refuses the profile flag —
do not trust unverified numbering. Numbering questions are settled against
LaTeX's own `.aux`: compile the draft once and compare label numbers with
`crosswalk/numbering-current.json`.

## Missing or stale declaration maps

`paperforge build web` names the missing map, whether a candidate exists,
and the acceptance command. After a formalization update, badges failing
`lean_links` mean the map needs regenerating — the update-formalization
skill is the checklist.

## Drift-gate failures (artifact_drift / trust table / version footers)

The fix is always the same: run the named generator and commit the result.
Build scripts run the generators before the checks, so a red gate in
`paperforge check` usually means a build was skipped after a manual edit
to a duplicated artifact.

## HTML enhancement failures

A postprocessing stage erroring with "PreTeXt output changed" means the
build refused to ship without a patch (lazy MathJax, ToC default) rather
than silently degrading — check your PreTeXt version against the exercised
range in `paperforge doctor`, and file/fix the pattern in
`paperforge/postprocess/web.py`.

Blank math inside dynamically opened panels, hovers without popups, or
stale UI after regenerating registries: hard-reload with a cache-busting
query — the built page's UI bundle is a single concatenated file and
browsers cache it aggressively.

## Review server safety

One review server per instance, ever: a second writer can corrupt decision
artifacts mid-write. `paperforge review` guards with a PID file
(`.cache/paperforge/review-server.pid`) and refuses a second start; if a
server crashed, remove the stale PID file. Server-side `/api/*` changes
need a restart; the injected JS reloads from disk per request.

## Missing optional dependencies

Optional binaries degrade, never block: no `pdftotext` skips pin
verification (warning), no `rsvg-convert` skips favicon rasters, no `npm`
means CDN MathJax instead of vendored. `paperforge doctor` lists each with
what it is for.

## Collecting a diagnostic bundle

For a bug report, capture:

```bash
paperforge doctor > doctor.txt 2>&1
paperforge status >> doctor.txt
paperforge build web --plan >> doctor.txt
python3 -m pip show paperforge pretext lxml >> doctor.txt
```

plus the failing command's full output. `output/build-provenance.json`
identifies the exact tool commit (and dirty state) of the last build.

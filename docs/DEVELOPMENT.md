# Paired development: paperforge + an active instance

The tool and its first instance evolve together. The design keeps that
fast (review §9): **schema compatibility is the hard gate; exact commit
pinning is opt-in and not implemented until a release needs it.**

## Setup

```bash
python3 -m pip install -e /path/to/paperforge        # editable: edits are live
python3 -m pip install -e /path/to/paperforge/validators
```

Because the install is editable, a change in the checkout is immediately
visible from every instance — no lock file, no reinstall. `paperforge
doctor` prints which checkout resolved and its commit + dirty state:

```text
OK      paperforge checkout: /Users/you/paperforge
INFO    checkout commit: abc1234 (dirty)
```

## The loop

```bash
cd ~/paperforge          # edit the tool
cd ~/my-paper
paperforge doctor        # confirms which checkout + state
paperforge build web
paperforge check
```

Dirty-tool builds are **reported, never blocked**: every build writes
`output/build-provenance.json` (tool commit + dirty flag, instance commit,
PreTeXt + Python versions) and the completion banner says
`paperforge abc1234+dirty`. A release-copy step must redact the local
`source` path from published provenance.

## Compatibility model

- `paper.toml [paperforge] instance_schema` is checked on every load;
  bumping it is a deliberate act accompanying a layout change, with
  `paperforge migrate` guidance for older instances.
- Old config keys keep loading (normalized, with deprecations listed by
  `doctor` and `migrate config` — not nagged on every build).
- Exact freezing (`paperforge freeze`/`verify lock`) is future, deliberate
  release machinery — never a default development constraint.

## Parity discipline

When generalizing instance behavior into the tool, prove byte parity
before deleting the instance copy: run the old path and the new path and
diff the tracked artifacts (the exercised instance's git status is the
cheapest oracle — a clean tree after a tool-driven rebuild IS the proof).
The public fixture (`examples/minimal-paper` + `tests/`) holds regression
snapshots so the next change can't silently undo it.

## Worktrees

Nothing assumes the checkout's directory name or branch: a feature
worktree installed editable into its own venv works, and `doctor` tells
you which one is active.

## Tests

```bash
python3 -m pytest tests/ -q        # units + the spaces-in-path smoke
```

CI (`.github/workflows/ci.yml`) runs the unit/bootstrap matrix on Ubuntu
and macOS plus a full fixture build with the PreTeXt CLI installed. The
private instance can't run in public CI — after tool changes, run the
instance's build + `paperforge check` locally and confirm a clean tree.

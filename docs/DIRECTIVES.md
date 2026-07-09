# The directive workflow

The single human-in-the-loop control surface. You never hand-edit the PreTeXt
source directly (though you can); instead you leave **directives** that Claude
applies. This keeps every change attributable and lets the whole document stay
Claude-maintained across input changes.

## Two channels

### 1. Inline markers — when you know *where*

Drop a PreTeXt/XML comment right at the point of interest:

```xml
<!-- @forge: this proof is too terse; expand to detail-level 2 -->
<!-- @forge:verbatim
     It was Deligne who first observed that ...   (this text is MINE, insert as-is)
-->
```

`apply-directives` finds every `@forge` comment, acts, and removes the marker.
Placement is unambiguous because the location *is* the instruction.

### 2. Sidecar queue — when placement needs to be found

Files in `directives/NNNN-slug.md`, for "add this somewhere appropriate":

```markdown
---
kind: instruct            # instruct | verbatim
target: thm-main-bound    # optional xml:id; omit to let Claude place it
section: background       # optional hint
---
Add a sentence noting that the bound is sharp for elliptic curves of
conductor 2, citing [Turturean].
```

For `target`-less directives Claude proposes a placement and inserts with a visible
marker you can relocate — it does not silently guess.

## verbatim vs instruct (this is also the plagiarism boundary)

- `verbatim` — text you wrote. Inserted essentially as-is. Safe by construction
  because it is *your* voice. Skips generation.
- `instruct` — an instruction to write. Goes through generation **and** the
  plagiarism validator ([PLAGIARISM.md](PLAGIARISM.md)).

Tagging the two differently is what lets the plagiarism guard stay meaningful:
generated prose is always checked; your own prose is never falsely flagged.

## Targeting and staleness

Directives target `xml:id`s. `validators/directives.py` fails if a directive names
a target id that no longer exists in the source — the same drift-safety idea as
the `<lean>` `checkdecls`. So a refactor that renames a section can't silently
misplace queued feedback.

## Provenance = git

`apply-directives` applies **one directive per commit**, the commit message
referencing the directive, then archives the consumed directive to
`directives/applied/`. The git history is therefore a complete, reviewable audit
trail of every non-verbatim insertion and its origin — the strongest available
answer to "did an LLM quietly introduce this text?".

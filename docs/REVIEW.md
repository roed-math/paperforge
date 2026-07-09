# The author review surface

Every judgment call the pipeline makes lives in a committed JSON artifact —
novelty claims, notation sense decisions, citation-need classifications,
formalized-known matches. Editing JSON is a fine interface for the pipeline
and a bad one for the author. Two review surfaces exist:

## 1. The review dashboard (primary)

    cd <instance>
    python3 <paperforge>/review/review_server.py
    # open http://127.0.0.1:8765/review

One tab per artifact, one card per decision: the statement (editable where
the artifact carries prose, e.g. novelty claims), structured evidence fields,
status buttons, and a free-text **note to the pipeline** persisted into the
artifact (`author_note`).

- **Knowl-style context**: each paper anchor opens *in place* as an
  expandable panel containing the anchored element from the built paper,
  typeset with the paper's own macro block (fetched from `output/web`); a
  small ↗ still opens the full page.
- **Help hovertext everywhere**: every field label and every status choice
  carries question-mark-style hover documentation (the adapters own the help
  text; the (?) after the choices shows the full legend) — the same idiom as
  the paper's notation hovers.
- **Everything autosaves**: status clicks save immediately; notes and
  statement edits save on a 700 ms debounce and on blur. There is no save
  button; a "saved ✓" flash confirms each write.
- **Citations are first-class**: the insert-citation picker shows each
  entry's author and title (not just the key); citation chips in the live
  preview hover to the full bibliography entry and — when a local copy is
  matched in `references/` (author-surname-gated filename matching) — click
  through to the PDF itself.

Decisions write back into the native artifact files immediately; there is no
second source of truth, no export step, and `git diff` shows exactly what the
author decided. The server is stdlib-only and binds to localhost.

## 2. In-chat batch review (complementary)

For a handful of pending items, asking Claude to "review the novelty claims
with me" is faster: Claude presents each pending item with its evidence and
records the answers into the same artifacts. Same files, same statuses —
the dashboard and chat are interchangeable.

## Contract for new decision artifacts

Any new judgment cache the pipeline grows should (a) key items by stable ids,
(b) carry a `status` whose value set includes an author-approved state,
(c) tolerate an `author_note` field, and (d) get an adapter class in
`review/review_server.py` (~30 lines). The dashboard picks it up as a tab.

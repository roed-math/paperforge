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
the artifact carries prose, e.g. novelty claims), the evidence bullets, the
current status, one-click status buttons, and a free-text **note to the
pipeline** persisted into the artifact (`author_note`). Crucially,每 card
links its paper anchors into the *built paper* (`/paper/...` serves
`output/web/`), so the anchored theorem — with notation hovers and lean
badges — is one click away while judging.

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

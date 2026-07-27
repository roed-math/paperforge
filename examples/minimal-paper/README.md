# minimal-paper: the public smoke fixture

The smallest instance that exercises the onboarding path end to end
(review §5-P1): a two-section amsart draft (theorem/lemma/definition/
remark/proof, a labeled and an unlabeled equation, one citation), a fake
Lean source tree the declaration-map miner can read without any Lean
toolchain (docstring and name-encoded citations, an axiom, a private
decl), and a one-key notation map.

Consumed by `tests/test_smoke.py`:

    paperforge init  (into a scratch dir WITH A SPACE in its path)
    paperforge doctor
    paperforge ingest --bootstrap     ->  numbering + candidate decl map
    paperforge accept lean-decl-map
    paperforge build web              (skipped when pretext is absent)

`expected/` holds regression snapshots of the deterministic artifacts
(current numbering, the candidate declaration map with file/line fields
normalized). If a converter change alters them INTENTIONALLY, regenerate
via the test's instructions and commit the new snapshots with the change.

This fixture is deliberately tiny; it exists to catch onboarding defects,
not to model real-paper complexity (multiple formalizations, badge caps,
snapshots, insertions, trust tables — the exercised instance covers those).

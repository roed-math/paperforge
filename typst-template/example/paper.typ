#import "../lib/paperforge.typ": *

#show: paper.with(
  title: [A Presentation of the Absolute Galois Group of $QQ_2$],
  authors: (
    (name: "A. Author", affiliation: "Department of Mathematics, Example University"),
  ),
  abstract: [
    We exhibit a finite presentation of $G_(QQ_2)$ and verify it against a
    machine-checked formalization. This example exercises every feature of the
    paperforge Typst backend: detail tiers, shared statement numbering,
    formalization badges, notation hovers and native MathML.
  ],
)

// The hover registry. A real instance GENERATES this from the document's own
// notation list rather than hand-writing it — same rule as the PreTeXt backend.
#notation-registry((
  GQ: (
    html: "<b>G<sub>ℚ₂</sub></b> — the absolute Galois group of the 2-adic numbers.",
    href: "#sec-intro",
  ),
  Gab: (
    html: "<b>G<sup>ab</sup></b> — the maximal abelian quotient of G.",
    href: "#sec-intro",
  ),
))

= Introduction <sec-intro>

The absolute Galois group $G_(QQ_2) = "Gal"(overbar(QQ)_2 \/ QQ_2)$ is a
profinite group of rank four. Our main result gives generators and relations.

#theorem(name: [Main Theorem], lean: ("GQ2.Presentation.main", "gq2-claude"))[
  There is an isomorphism $Gamma tilde.equiv G_(QQ_2)$ of profinite groups,
  where $Gamma$ is the profinite group presented by four generators subject to
  one relation.
] <thm-main>

#proof(of: [@thm-main])[
  The proof combines the counting argument of @lem-count with the
  reconstruction step.

  #detail(2)[
    In more detail: the counting argument produces a surjection
    $Gamma arrow.twohead G_(QQ_2)$, and Lemma #ref(<lem-count>) shows both
    groups have the same number of open subgroups of each index. A profinite
    group is Hopfian, so the surjection is an isomorphism.
  ]

  #detail(3, summary: [the full cocycle computation])[
    The cocycle is the one transported along the boundary map
    $ delta : H^1(G, M) --> H^2(G, M') $ <eq-boundary>
    and the class of @eq-boundary vanishes because $H^2$ is cyclic of order two.
  ]
]

Notation is marked so a reader can recall a definition without scrolling back:
$ #notn("GQ", $G_(QQ_2)$) arrow.twohead #notn("Gab", $G^("ab")$) $ <eq-ab>

See @eq-ab and @sec-counting below. (A reference from here into the level-3
block above would be a build error in a `--input detail=1` PDF, where that
block is not emitted — see `docs/TYPST-BACKEND.md`.)

== A subsection <sec-sub>

Ordinary prose with an inline aside#detail-inline(2)[ — which only a reader at
detail level two sees — ]and then the sentence continues.

= The counting argument <sec-counting>

#lemma(lean: "GQ2.Counting.index_eq")[
  For every $n$, the group $Gamma$ has exactly as many open subgroups of index
  $n$ as $G_(QQ_2)$ does.
] <lem-count>

#proof[
  Both counts are given by the same mass formula.
  #detail(2)[
    Serre's mass formula computes the number of extensions of $QQ_2$ of degree
    $n$ inside a fixed algebraic closure; the group-theoretic side is
    #cite(<serre-mass>, supplement: [Thm. 2]).
  ]
]

#definition[
  A profinite group is _Hopfian_ if every continuous surjective endomorphism is
  an isomorphism.
] <def-hopfian>

#remark[
  @def-hopfian is where finite generation is used; the statement is false for
  general profinite groups.
] <rem-hopfian>

#figure(
  table(
    columns: 3,
    table.header([$n$], [subgroups of $Gamma$], [subgroups of $G_(QQ_2)$]),
    [1], [1], [1],
    [2], [7], [7],
    [4], [45], [45],
  ),
  caption: [Open subgroups of small index.],
) <tab-counts>

@tab-counts was computed with the formalization#footnote[The tables agree for
all $n <= 64$.].

#bibliography("refs.bib", title: [References])

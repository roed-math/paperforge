// Theorem-like environments with an amsart-style shared counter.
//
// Every environment is a `figure` with the SAME `kind`, so they share one
// counter (Theorem 1.1, Lemma 1.2, Definition 1.3, ...) exactly as amsart's
// `\newtheorem{lemma}[theorem]{Lemma}` does, while each keeps its own
// supplement for references.
//
// Numbering subtlety, learned the hard way: a `figure(numbering: ..)` function
// that reads `counter(heading)` is evaluated wherever it is DISPLAYED, so
// references print the section number of the referring site, not the target's
// (`@thm-main` in section 8 rendered as "Theorem 8.1"). Both the block header
// and the `show ref` rule below therefore resolve the number explicitly at the
// target's own location.

#import "config.typ": draft, html-detail-default
#import "lean.typ": lean

// `lean:` on a statement takes a declaration name, a `(decl, project)` pair, or
// an array of either.
#let _lean-badges(spec) = {
  let items = if type(spec) == array and (spec.len() == 0 or type(spec.at(0)) != str
    or spec.len() > 2) { spec } else if type(spec) == array { (spec,) } else { (spec,) }
  for d in items {
    if type(d) == str { lean(d) }
    else if type(d) == array { lean(d.at(0), project: d.at(1, default: none)) }
    else { lean(..d) }
  }
}

#let thm-kind = "pf-statement"
#let thm-counter = counter(figure.where(kind: thm-kind))

/// The printed number of a statement at `loc`: section number, then the shared
/// counter. Context-free by construction — safe to call from a `show ref`.
#let statement-number(loc) = numbering(
  "1.1",
  counter(heading).at(loc).first(),
  thm-counter.at(loc).first(),
)

// Per-kind presentation. `body-style` mirrors amsart: statements italic,
// definitions and remarks upright.
#let _styles = (
  theorem: (supplement: "Theorem", italic: true),
  lemma: (supplement: "Lemma", italic: true),
  proposition: (supplement: "Proposition", italic: true),
  corollary: (supplement: "Corollary", italic: true),
  conjecture: (supplement: "Conjecture", italic: true),
  definition: (supplement: "Definition", italic: false),
  remark: (supplement: "Remark", italic: false),
  example: (supplement: "Example", italic: false),
  notation: (supplement: "Notation", italic: false),
  question: (supplement: "Question", italic: false),
)

/// Build one environment constructor.
///
///   #let theorem = statement("theorem")
///   #theorem[...] <thm-main>
///   #theorem(name: [Main Theorem])[...] <thm-main>
#let statement(kind-name) = {
  let style = _styles.at(kind-name)
  (body, name: none, lean: none) => figure(
    kind: thm-kind,
    supplement: style.supplement,
    caption: none,
    // metadata travels with the element so the show rule can style per kind
    // even though every kind shares one figure kind.
    [#metadata((kind: kind-name, name: name, italic: style.italic, lean: lean))#body],
  )
}

#let theorem = statement("theorem")
#let lemma = statement("lemma")
#let proposition = statement("proposition")
#let corollary = statement("corollary")
#let conjecture = statement("conjecture")
#let definition = statement("definition")
#let remark = statement("remark")
#let example = statement("example")
#let notation-stmt = statement("notation")
#let question = statement("question")

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

// The body we stored is `metadata(..) + real body`; split it back apart.
#let _split(body) = {
  let children = if body.has("children") { body.children } else { (body,) }
  let meta = none
  let rest = ()
  for c in children {
    if meta == none and c.func() == metadata { meta = c.value } else { rest.push(c) }
  }
  (meta: if meta == none { (kind: "theorem", name: none, italic: true, lean: none) } else { meta },
   body: rest.join())
}

#let statement-rules(doc) = {
  show figure.where(kind: thm-kind): it => {
    let parts = _split(it.body)
    let head = context [#it.supplement #statement-number(it.location())]
    let named = if parts.meta.name != none [ (#parts.meta.name)] else []

    context if target() == "html" {
      // Typst only emits an `id` for elements something references. paperforge
      // needs one on EVERY statement — deep links, margin-review anchors and
      // click-to-mark all address statements by tag — so set it from the label.
      let lbl = it.at("label", default: none)
      let attrs = (
        class: "pf-stmt pf-stmt-" + parts.meta.kind,
        "data-kind": parts.meta.kind,
      )
      if lbl != none { attrs.insert("id", str(lbl)) }
      html.elem("div", attrs: attrs, {
        html.elem("span", attrs: (class: "pf-stmt-head"), [#head#named.])
        if parts.meta.lean != none {
          html.elem("span", attrs: (class: "pf-stmt-badges"), _lean-badges(parts.meta.lean))
        }
        html.elem("div", attrs: (class: "pf-stmt-body"), parts.body)
      })
    } else {
      block(width: 100%, above: 1.1em, below: 1.1em, {
        strong[#head#named.]
        h(0.4em)
        if parts.meta.italic { emph(parts.body) } else { parts.body }
      })
    }
  }

  // References resolve the number at the TARGET's location.
  show ref: it => {
    let el = it.element
    if el != none and el.func() == figure and el.kind == thm-kind {
      let sup = if it.supplement == auto { el.supplement } else { it.supplement }
      link(el.location(), context [#sup #statement-number(el.location())])
    } else { it }
  }

  doc
}

// ---------------------------------------------------------------------------
// Proofs
// ---------------------------------------------------------------------------

/// A proof. Always present in the PDF; a collapsible disclosure in HTML, wired
/// to the same detail slider as `#detail` blocks (proofs sit at level 1).
#let proof(body, of: none, level: 1, open: auto) = context {
  let head = if of == none [Proof] else [Proof of #of]
  if target() == "html" {
    let is-open = if open == auto { level <= html-detail-default } else { open }
    let attrs = (class: "pf-proof", "data-detail-level": str(level))
    if is-open { attrs.insert("open", "open") }
    html.elem("details", attrs: attrs, {
      html.elem("summary", attrs: (class: "pf-proof-summary"), head)
      html.elem("div", attrs: (class: "pf-proof-body"), body)
    })
  } else {
    block(width: 100%, above: 1.1em, below: 1.1em, {
      emph[#head.]
      h(0.4em)
      body
      h(1fr)
      sym.square.stroked
    })
  }
}

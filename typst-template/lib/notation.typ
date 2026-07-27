// Notation links: hover a symbol, see where it was defined.
//
// The PreTeXt backend routes this through a MathJax `\class` macro, because
// MathJax owns the rendered math. Typst emits MathML directly, so the marker
// can be a real element in the math tree — `html.elem("mrow", ..)` is valid
// MathML Core, unlike a `<span>` wrapper (which would put an HTML element
// inside `<math>` and break rendering in browsers that validate the tree).

#import "config.typ": draft

#let _classes(far, defsite) = {
  let c = "pf-notn"
  if far { c += " pf-notn-far" }
  if defsite { c += " pf-notn-defsite" }
  c
}

/// Mark an occurrence of a notation that sits INSIDE a `$..$`. `key` indexes
/// the registry; `sym` is the math content it wraps. Invisible until hover.
///
///   $ #notn("GQ", $G_(QQ_2)$) -> #notn("WA", $W_A$) $
///
/// This emits an `<mrow>`, which is valid only inside `<math>`. For a symbol
/// standing on its own in prose use `notn-inline` — see the warning there.
#let notn(key, sym, far: false, defsite: false) = context {
  if target() != "html" { return sym }
  html.elem("mrow", attrs: (
    class: _classes(far, defsite),
    "data-notn": key,
  ), sym)
}

/// Mark a notation occurrence that stands ALONE IN PROSE, e.g.
///
///   Exponentiation by an element of #notn-inline("Zhat", $hat(bold(Z))$) ...
///
/// Do not reach for `notn` here. Outside `$..$` there is no enclosing `<math>`
/// for an `<mrow>` to live in, and Typst responds by dropping the parts it
/// cannot express — "accent was ignored during HTML export", "attach was
/// ignored during HTML export" — so `Ẑ` silently exports as a bare `Z` and
/// `G_(Q_2)` as a bare `G`. The `<span>` wrapper keeps the math element intact.
#let notn-inline(key, sym, far: false, defsite: false) = context {
  if target() != "html" { return sym }
  html.elem("span", attrs: (
    class: _classes(far, defsite),
    "data-notn": key,
  ), sym)
}

/// A notation whose definition is far back in the document: gets a visible
/// dotted underline, because a reader has no reason to suspect a hover here.
#let notn-far(key, sym) = notn(key, sym, far: true)

/// The defining occurrence. Rendered with the "≝" affordance so a reader who
/// followed a hover here can see they have arrived.
#let notn-def(key, sym) = notn(key, sym, defsite: true)

/// Same marker for notation that appears in prose rather than math.
#let term(key, body) = context {
  if target() != "html" { return body }
  html.elem("span", attrs: (class: "pf-term", "data-notn": key), body)
}

/// Emit the notation registry the hover JS reads. `entries` maps a key to a
/// dictionary with `html` (the definition to show) and optionally `href` (a
/// "see it in context" target).
///
/// Real instances should GENERATE this from the document rather than hand-write
/// it — same rule as the PreTeXt backend's notation registry.
#let notation-registry(entries) = context {
  if target() != "html" { return }
  html.elem("script", attrs: (type: "application/json", id: "pf-notation-registry"),
    json.encode(entries))
}

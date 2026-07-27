// Math constructs Typst's MathML export does not yet cover.
//
// A battery of the constructs a number-theory paper actually uses — accents,
// blackboard/calligraphic/fraktur alphabets, matrices, cases, big operators,
// stretched arrows, fractions, roots, binomials, attachments, underbraces,
// squiggly arrows — exports cleanly. As of Typst 0.15 exactly one fails, with
// `warning: overline was ignored during MathML export`.

/// `overline`, exported as MathML.
///
/// Typst's own `overline` silently vanishes from HTML. This emits the MathML
/// `<mover>` the browser needs and defers to the built-in for the paged target,
/// so `overbar(QQ)_2` looks the same in both.
///
/// (`macron(x)` — i.e. `\bar x` — already exports correctly and needs no shim.)
///
/// NB the name carries no hyphen on purpose: inside math mode Typst parses
/// `over-bar(x)` as the subtraction `over - bar(x)`, so a hyphenated shim
/// silently renders as literal text instead of calling the function.
/// Hand-rolling the `<mover>` is tempting and wrong: a string passed to
/// `html.elem` inside math mode is realized as `<mtext>`, and the resulting
/// `<mo><mtext>‾</mtext></mo>` renders as a bar floating off to the side.
/// Typst's `macron` already emits the correct `<mover accent="true">`, so the
/// shim just routes to whichever of the two the target supports.
#let overbar(body) = context {
  if target() == "html" { math.macron(body) } else { overline(body) }
}

// To use the shim under the built-in's name throughout a document, rebind it
// once at the top of the source (a show rule cannot intercept a function call):
//
//   #let overline = overbar

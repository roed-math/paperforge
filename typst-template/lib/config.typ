// Build-time configuration, read from `typst compile --input key=value`.
//
// The whole point of the Typst backend is that ONE authored source serves both
// targets. Everything that differs between them is either a `--input` (the PDF
// side, resolved at compile time) or a data attribute the browser reads (the
// HTML side, resolved at read time).

#let _input(key, default) = sys.inputs.at(key, default: default)

/// Detail level baked into a PDF build: blocks tagged with a level ABOVE this
/// are not emitted at all. Ignored by the HTML target, which always emits every
/// block and lets the reader move the slider.
///
/// `typst compile paper.typ --input detail=3 paper-full.pdf`
#let detail-level = int(_input("detail", "1"))

/// Level at which a `#detail` block is born open in HTML (the slider's initial
/// position). Independent of `detail-level` so one HTML build can ship with a
/// gentler default than the PDF.
#let html-detail-default = int(_input("html-detail", "1"))

/// Where the generated Lean API docs live, relative to the HTML output. Empty
/// disables badge links (they degrade to inert pills).
#let lean-docs-root = _input("lean-docs", "lean")

/// Default Lean project name for `#lean(..)` badges that do not name one.
#let lean-default-project = _input("lean-project", "")

/// Draft mode: show detail-level tags and other authoring affordances.
#let draft = _input("draft", "0") != "0"

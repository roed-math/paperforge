# Style corpus

Drop the author's **own** prior mathematical writing here — introductions,
expository passages, papers whose voice the generated prose should match.

**Prefer `.tex` source over PDFs.** Mathematical prose is exactly where PDF
text extraction is worst: inline math garbles into noise tokens mid-sentence,
hyphenation and ligatures corrupt words, and structure (where an introduction
starts, how a proof is paragraphed) is lost. LaTeX source preserves the whole
authorial layer — sentence rhythm around math, transition habits, how theorems
are stated and proofs opened — which is precisely what the generative skills
imitate. It is also far cheaper for the model to read. For your own arXiv
papers, download the source tarball (arXiv → "Other formats" → Source), not
the PDF. PDFs are an acceptable fallback when no source survives.

Generative skills read this to imitate *your* register, sentence rhythm, and
idiom. It is deliberately separate from `references/` (works you *cite*): the
corpus is a voice model to imitate; references are sources you must **not** copy
from (see ../../docs/PLAGIARISM.md).

`ADVICE.md` (next to this file) holds free-text guidance on good mathematical
writing that every skill also reads.

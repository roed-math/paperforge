# Publisher policies on AI-assisted mathematical writing

A survey of how mathematics publishers treat AI assistance in authoring, for
deciding where and how a paperforge-produced paper can be submitted.
**Surveyed 2026-07-11.** These policies are moving targets: re-verify against
the publisher's own page before submission. Corrections welcome.

## The common ground

Every publisher surveyed agrees on three points:

1. **AI cannot be an author.** Authorship requires accountability — the
   capacity to approve the final version, hold copyright, and answer for
   errors — which tools cannot carry. This position originates with the
   [COPE position statement on Authorship and AI tools](https://publicationethics.org/guidance/cope-position/authorship-and-ai-tools)
   and has been adopted essentially verbatim across the industry.
2. **Humans carry full responsibility** for all content however it was
   produced — including AI-introduced errors, fabricated references, and
   plagiarized passages.
3. **Substantive use must be disclosed.** Where and how varies (see below);
   pure grammar/spell-checking is usually exempt.

The divergence is in the details: what counts as disclosable use, where the
disclosure goes, whether AI-generated figures are permitted, and how much
generative drafting is tolerated.

## By publisher

| Publisher | Mathematics venues | AI authorship | Disclosure | Notes |
|---|---|---|---|---|
| [AMS](https://www.ams.org/about-us/CPub_AI-WhitePaper.pdf) | JAMS, Transactions, Proceedings, Notices, Bulletin, Math. Comp. | No (adopted COPE) | Required, full disclosure of usage | Amended its *Ethical Guidelines and Journal Policies* with an AI-in-authoring section; runs an [Advisory Group on AI and the Mathematical Community](https://www.ams.org/about-us/CPub_AI-WhitePaper.pdf). The white paper *Artificial Intelligence: Publishing in Mathematics* is the fullest statement by any math society. |
| [SIAM](https://epubs.siam.org/artificial-intelligence) | SIAM journal portfolio | No | Required | Distinctively mathematical: warns that AI produces plausible-but-wrong proofs and derivations, and places correctness squarely on authors, not referees; AI-generated summaries in related-work sections flagged as a fabrication risk; figures must come from verifiable, reproducible processes. |
| [Elsevier](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals) | JNT, JPAA, J. Algebra, Advances, Topology Appl., … | No | Mandatory titled declaration section before the references, with a [fixed template](https://www.elsevier.com/about/policies-and-standards/the-use-of-generative-ai-and-ai-assisted-technologies-in-writing-for-elsevier) (tool, reason, statement of human review) | Drafting assistance allowed "with oversight"; grammar/spelling tools exempt; generative images prohibited; reviewers may not upload manuscripts to AI tools. |
| [Springer Nature](https://www.springernature.com/gp/policies/editorial-policies) | Inventiones, Math. Annalen, GAFA, Combinatorica, … | No | Document generative use (Methods or equivalent); *AI-assisted copy editing* explicitly exempt | No generative images; peer reviewers barred from uploading manuscripts. One centralized policy across the 3000-journal portfolio. |
| [Wiley](https://www.wiley.com/en-us/publish/article/ai-guidelines/) | Bull./J. LMS (publishing partner), CPAM, JGT, … | No | Required for substantive use | Standard COPE-aligned position; note that society journals published *through* Wiley (e.g. LMS journals) may layer society-specific guidance on top. |
| [Taylor & Francis](https://taylorandfrancis.com/our-policies/ai-policy/) | Experimental Math., Comm. Algebra, … | No | Required: tool name **and version**, how used, why | The most prescriptive disclosure format of the group. |
| [Cambridge UP](https://www.cambridge.org/core/services/publishing-ethics/research-publishing-ethics-guidelines-for-journals/authorship-and-contributorship) | Compositio (host), Forum of Math. Pi/Sigma, J. Inst. Math. Jussieu, … | No | Declare and explain AI use "as with other software, tools and methodologies" | Frames AI as methodology; accountability rationale for the authorship bar. |
| [arXiv](https://blog.arxiv.org/2023/01/31/arxiv-announces-new-policy-on-chatgpt-and-similar-tools/) | (preprints — where the paper meets readers first) | No — tools cannot be listed as authors | Report "significant use of sophisticated tools," explicitly including text-to-text generative AI, per subject-area methodological norms | Since 2026, [enforced](https://www.researchinformation.info/news/arxiv-imposes-one-year-ban-for-unchecked-ai-generated-content/): incontrovertibly unchecked LLM content (hallucinated references, misleading content) draws a one-year submission ban, after a study found ~150k hallucinated references in one year of preprints ([coverage](https://www.insidehighered.com/news/faculty/books-publishing/2026/05/22/ban-authors-who-submit-ai-content-welcome-unenforceable)). |
| EMS Press | J. EMS, Comment. Math. Helv. (host), … | — | — | No public AI policy located at survey time; assume COPE norms and ask the handling editor. |
| Princeton/IAS (Annals), Duke UP | Annals of Math., Duke Math. J. | — | — | No dedicated public AI policy located at survey time; same advice. |

## What this means for a paperforge paper

paperforge's architecture is designed so that the disclosure these policies
require is *generated, not reconstructed*:

- **Provenance is recorded at write time** — every generative pass commits
  with a `Generated-by:` trailer, proposal artifacts carry per-item
  `generator` fields, and the planned development record publishes the
  ticket-level timeline. An Elsevier-style declaration or an
  arXiv-style tool report can be assembled mechanically from this record.
- **Human accountability has a control surface** — nothing generative
  reaches the paper without passing the author review dashboard, which is
  precisely the oversight the policies demand.
- **The plagiarism validator** (n-gram overlap against the reference
  library, findings labeled inherited-vs-pipeline-added) addresses the
  fabrication/plagiarism failure mode the arXiv enforcement targets, and the
  references validator pins citations against local copies of the cited
  works — the direct countermeasure to hallucinated references.

When preparing a submission, start from the target venue's row above, then
generate the disclosure statement from the git/provenance record rather than
writing it from memory.

<?xml version="1.0" encoding="UTF-8"?>
<!-- Journal-ready (amsart-style) LaTeX via PreTeXt's experimental
     pretext-latex-classic conversion. paper-init rewrites the placeholder
     from paper.toml [build] (sibling of pretext_core_xsl).
     UPSTREAM BUG WORKAROUND: classic emits booktabs rules for <tabular>
     without loading the package. \class is MathJax-only (notation hovers);
     the providecommand makes it a no-op wrapper in LaTeX. -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="@@PRETEXT_CORE_LATEX_CLASSIC_XSL@@"/>
  <xsl:param name="latex.preamble.early"
             select="'\usepackage{booktabs}&#xa;\providecommand{\class}[2]{#2}'"/>
  <xsl:variable name="author-metadata"
                select="document('../content/authors.xml', /)/author-metadata"/>
  <!-- PDF metadata lists every author (title/subject come from core) -->
  <xsl:param name="latex.preamble.late">
    <xsl:text>\hypersetup{pdfauthor={</xsl:text>
    <xsl:for-each select="/pretext/article/frontmatter/titlepage/author">
      <xsl:if test="position() &gt; 1"><xsl:text> and </xsl:text></xsl:if>
      <xsl:value-of select="personname"/>
    </xsl:for-each>
    <xsl:text>}}</xsl:text>
  </xsl:param>
  <!-- formalization badges are an HTML feature; drop in journal LaTeX -->
  <xsl:template match="lean"/>
  <!-- prose term links are an HTML feature; keep only their text here -->
  <xsl:template match="termref"><xsl:apply-templates/></xsl:template>
  <!-- alphabetic bibliography labels (tex2ptx bib-labels option) -->
  <xsl:template match="biblio[@label]" mode="serial-number">
    <xsl:value-of select="@label"/>
  </xsl:template>
  <!-- same as core's references template, except thebibliography's
       widest-label argument is the longest actual label -->
  <xsl:template match="references">
    <xsl:apply-templates select="." mode="console-typeout"/>
    <xsl:text>\bibliographystyle{</xsl:text>
    <xsl:value-of select="$bibliographystyle"/>
    <xsl:text>}&#xa;</xsl:text>
    <xsl:text>\begin{thebibliography}{</xsl:text>
    <xsl:choose>
      <xsl:when test="biblio[@label]">
        <xsl:for-each select="biblio[@label]">
          <xsl:sort select="string-length(@label)" data-type="number"
                    order="descending"/>
          <xsl:if test="position() = 1">
            <xsl:value-of select="@label"/>
          </xsl:if>
        </xsl:for-each>
      </xsl:when>
      <xsl:otherwise><xsl:text>99</xsl:text></xsl:otherwise>
    </xsl:choose>
    <xsl:text>}&#xa;</xsl:text>
    <xsl:apply-templates select="*"/>
    <xsl:text>\end{thebibliography}&#xa;</xsl:text>
  </xsl:template>

  <!-- UPSTREAM BUG WORKAROUND: for an author with an affiliation, classic
       emits the affiliation's trailing newline AND its own, leaving a blank
       line inside \author{...}. \author is not \long, so the \par is a LaTeX
       error and the whole author block silently vanishes from \maketitle.
       Identical to core except the trailing newline is a comment-newline,
       which TeX eats. -->
  <xsl:template match="author" mode="article-frontmatter">
    <xsl:apply-templates select="personname" />
    <xsl:if test="support">
        <xsl:text>\thanks{</xsl:text>
        <xsl:apply-templates select="support" />
        <xsl:text>}</xsl:text>
    </xsl:if>
    <xsl:if test="affiliation">
        <xsl:text>\\&#xa;</xsl:text>
        <xsl:apply-templates select="affiliation" />
    </xsl:if>
    <xsl:if test="email">
        <xsl:text>\\&#xa;</xsl:text>
        <xsl:apply-templates select="email" mode="article-info"/>
    </xsl:if>
    <xsl:if test="following-sibling::author" >
        <xsl:text>%&#xa;\and</xsl:text>
    </xsl:if>
    <xsl:text>%&#xa;</xsl:text>
  </xsl:template>

  <!-- Author-status footnotes (content/authors.xml author-footnote records):
       the marker belongs to the affiliation that carries it, so the note is
       emitted after \maketitle rather than through \thanks, which would add
       a second marker beside the author's name. -->
  <xsl:template name="author-status-footnotes">
    <xsl:for-each select="$author-metadata/record[author-footnote]">
      <xsl:text>\begingroup&#xa;</xsl:text>
      <xsl:text>\renewcommand{\thefootnote}{\fnsymbol{footnote}}&#xa;</xsl:text>
      <xsl:text>\footnotetext[</xsl:text>
      <xsl:value-of select="position()"/>
      <xsl:text>]{</xsl:text>
      <xsl:apply-templates select="author-footnote/node()"/>
      <xsl:text>}&#xa;</xsl:text>
      <xsl:text>\endgroup&#xa;</xsl:text>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="bibinfo-post-begin-document">
    <xsl:text>\maketitle&#xa;</xsl:text>
    <xsl:call-template name="author-status-footnotes"/>
    <xsl:apply-templates select="$document-root/frontmatter/abstract" mode="article-frontmatter"/>
    <!-- long papers need a table of contents in the PDF (the interactive
         edition has its own TOC UI) -->
    <xsl:text>\setcounter{tocdepth}{2}&#xa;</xsl:text>
    <xsl:text>\tableofcontents&#xa;</xsl:text>
  </xsl:template>

  <!-- UPSTREAM BUG WORKAROUND: classic's generic division template emits
       `\appendix{Title}` for <appendix>, but \appendix takes no argument in
       the article class — the title typesets as body text (headings run into
       prose) and \label picks up a stale counter, so cross-references print
       "Appendix 11" / "Appendix .9". After backmatter's one bare \appendix
       switch, each appendix division is simply a \section: lettered A, B, ...
       with subsections A.1 and theorem/equation numbers A.x. Identical to
       the core template otherwise. -->
  <xsl:template match="appendix">
    <xsl:apply-templates select="." mode="console-typeout"/>
    <xsl:text>\section{</xsl:text>
    <xsl:apply-templates select="." mode="title-full"/>
    <xsl:text>}\label{</xsl:text>
    <xsl:apply-templates select="." mode="unique-id" />
    <xsl:text>}%&#xa;</xsl:text>
    <xsl:apply-templates select="*"/>
    <xsl:text>% end of appendix: </xsl:text>
    <xsl:apply-templates select="." mode="title-full"/>
    <xsl:text>&#xa;</xsl:text>
  </xsl:template>
</xsl:stylesheet>

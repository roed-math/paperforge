<?xml version="1.0" encoding="UTF-8"?>
<!-- Default PreTeXt LaTeX conversion + paperforge custom-element handling.
     paper-init rewrites the placeholder from paper.toml [build]. -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="@@PRETEXT_CORE_LATEX_XSL@@"/>
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
  <!-- formalization badges are an HTML feature; drop in print -->
  <xsl:template match="lean"/>
  <!-- prose term links are an HTML feature; keep only their text here -->
  <xsl:template match="termref"><xsl:apply-templates/></xsl:template>
  <!-- alphabetic bibliography labels (tex2ptx bib-labels option) -->
  <xsl:template match="biblio[@label]" mode="serial-number">
    <xsl:value-of select="@label"/>
  </xsl:template>
  <!-- \class is MathJax-only; make it a no-op wrapper in LaTeX. Generated
       tables use booktabs rules, so load the package explicitly here as in
       the classic arXiv conversion. -->
  <xsl:param name="latex.preamble.early"
             select="'\usepackage{booktabs}&#xa;\providecommand{\class}[2]{#2}'"/>

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

  <xsl:template match="article/frontmatter/titlepage">
    <xsl:text>\maketitle&#xa;</xsl:text>
    <xsl:call-template name="author-status-footnotes"/>
    <xsl:text>\thispagestyle{empty}&#xa;</xsl:text>
  </xsl:template>
</xsl:stylesheet>

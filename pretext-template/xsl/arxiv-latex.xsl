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
</xsl:stylesheet>

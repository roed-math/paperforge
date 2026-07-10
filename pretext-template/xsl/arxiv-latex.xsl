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

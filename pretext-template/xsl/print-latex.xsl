<?xml version="1.0" encoding="UTF-8"?>
<!-- Default PreTeXt LaTeX conversion + paperforge custom-element handling.
     paper-init rewrites the placeholder from paper.toml [build]. -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="@@PRETEXT_CORE_LATEX_XSL@@"/>
  <xsl:param name="latex.preamble.early"
             select="'\providecommand{\class}[2]{#2}'"/>
  <!-- formalization badges are an HTML feature; drop in print -->
  <xsl:template match="lean"/>
  <!-- prose term links are an HTML feature; keep only their text here -->
  <xsl:template match="termref"><xsl:apply-templates/></xsl:template>
  <!-- alphabetic bibliography labels (tex2ptx bib-labels option) -->
  <xsl:template match="biblio[@label]" mode="serial-number">
    <xsl:value-of select="@label"/>
  </xsl:template>
</xsl:stylesheet>

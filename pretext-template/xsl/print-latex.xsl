<?xml version="1.0" encoding="UTF-8"?>
<!-- Default PreTeXt LaTeX conversion + paperforge custom-element handling.
     paper-init rewrites the placeholder from paper.toml [build]. -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="@@PRETEXT_CORE_LATEX_XSL@@"/>
  <xsl:param name="latex.preamble.early"
             select="'\providecommand{\class}[2]{#2}'"/>
  <!-- formalization badges are an HTML feature; drop in print -->
  <xsl:template match="lean"/>
</xsl:stylesheet>

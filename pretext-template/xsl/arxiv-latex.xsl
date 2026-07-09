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
</xsl:stylesheet>

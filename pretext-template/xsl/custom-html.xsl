<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0">

  <!-- Import the core PreTeXt HTML conversion and add/override templates.
       PLACEHOLDER: paper-init rewrites this href from paper.toml [build]
       pretext_core_xsl. See docs/HTML-FEATURES.md for the portable-import
       follow-up (the goal is to stop hardcoding an absolute path). -->
  <xsl:import href="@@PRETEXT_CORE_XSL@@"/>

  <!-- Inject the UI enhancement layer (slider + notation hovers) into every page.
       html.*.extra only emit the <script>/<link> tags; the files must be copied
       into the web output dir as a build step (see docs/HTML-FEATURES.md). -->
  <xsl:param name="html.css.extra" select="'detail-ui.css paper-style.css'"/>
  <xsl:param name="html.js.extra"  select="'detail-ui.js'"/>

  <!-- PLACEHOLDER: paper-init sets this from paper.toml [inputs] lean_docs_base. -->
  <xsl:param name="lean.docs.base" select="'@@LEAN_DOCS_BASE@@'"/>

  <!-- (1) Inline <lean ref="Namespace.decl">label</lean> -> link to the
       formalization, tagged for a later hover/knowl enhancement. -->
  <xsl:template match="lean">
    <a class="lean-link"
       href="{concat($lean.docs.base, @ref, '.html')}"
       data-lean-ref="{@ref}"
       title="Formalized as {@ref}">
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- (2) Detail tiers: stamp a `detail-level-N` class onto any element that
       carries @detail-level, so the client-side slider can target it. This is
       the single, non-invasive override point; core builds the rest of the
       class list (including `born-hidden-knowl`) via apply-imports. -->
  <xsl:template match="*[@detail-level]" mode="body-css-class">
    <xsl:apply-imports/>
    <xsl:text> detail-level-</xsl:text>
    <xsl:value-of select="@detail-level"/>
  </xsl:template>

  <!-- (2b) Paragraph tiers: core's <p> body hardcodes class="para" and never
       consults body-css-class, but it does call add-lude-parent-class inside
       the class attribute — piggyback on that so <p detail-level="N"> (the
       woven-in proof-detail paragraphs) gets the tier class too. -->
  <xsl:template match="p[@detail-level]" mode="add-lude-parent-class">
    <xsl:apply-imports/>
    <xsl:text> detail-level-</xsl:text>
    <xsl:value-of select="@detail-level"/>
  </xsl:template>

</xsl:stylesheet>

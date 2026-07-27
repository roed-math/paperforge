<?xml version="1.0" encoding="UTF-8"?>
<!--
  Replace tex2ptx's lossy author extraction with the instance's canonical
  overrides in content/authors.xml.  Authors with no matching record, and all
  other frontmatter nodes, are copied unchanged.  The transformation is
  idempotent (a replaced author still matches its record's aliases) and fails
  closed unless every record matches exactly one generated author and no
  author matches two records.
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="xml" encoding="UTF-8" indent="no"/>
  <xsl:strip-space elements="author affiliation"/>

  <xsl:variable name="author-metadata"
                select="document('../content/authors.xml', /)/author-metadata"/>

  <xsl:template match="/">
    <xsl:variable name="titlepage-authors"
                  select="pretext/article/frontmatter/titlepage/author"/>
    <xsl:if test="not($author-metadata/record)">
      <xsl:message terminate="yes">author metadata must declare at least one record</xsl:message>
    </xsl:if>
    <xsl:for-each select="$author-metadata/record">
      <xsl:if test="count(author) != 1">
        <xsl:message terminate="yes">
          <xsl:text>author record must contain exactly one author element: </xsl:text>
          <xsl:value-of select="@key"/>
        </xsl:message>
      </xsl:if>
      <xsl:variable name="aliases" select="aliases/personname"/>
      <xsl:if test="count($titlepage-authors[personname = $aliases]) != 1">
        <xsl:message terminate="yes">
          <xsl:text>expected exactly one draft author matching record: </xsl:text>
          <xsl:value-of select="@key"/>
        </xsl:message>
      </xsl:if>
    </xsl:for-each>
    <xsl:for-each select="$titlepage-authors">
      <xsl:variable name="name" select="personname"/>
      <xsl:if test="count($author-metadata/record[aliases/personname = $name]) &gt; 1">
        <xsl:message terminate="yes">
          <xsl:text>draft author matches more than one record: </xsl:text>
          <xsl:value-of select="$name"/>
        </xsl:message>
      </xsl:if>
    </xsl:for-each>
    <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="article/frontmatter/titlepage/author">
    <xsl:variable name="name" select="personname"/>
    <xsl:variable name="record"
                  select="$author-metadata/record[aliases/personname = $name]"/>
    <xsl:choose>
      <xsl:when test="$record">
        <xsl:copy-of select="$record/author"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:copy>
          <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
</xsl:stylesheet>

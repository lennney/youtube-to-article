"""Tests for processor components."""
import pytest
from ytarticle.core.schema import make_item, ContentItem, SeoMetadata
from ytarticle.components.processors.ai_rewrite import AIRewrite
from ytarticle.components.processors.seo_metadata import SeoMetadata as SeoMetadataComp
from ytarticle.components.processors.html_render import HtmlRender


class TestAIRewrite:
    def test_component_name(self):
        comp = AIRewrite()
        assert comp.name == "ai_rewrite"

    def test_parse_metadata(self):
        text = """<!-- METADATA
title: Test Article
difficulty: easy
time: 30 minutes
cost: $10
materials: glue, paper, scissors
-->"""
        meta = AIRewrite._parse_metadata(text)
        assert meta["title"] == "Test Article"
        assert meta["difficulty"] == "easy"

    def test_strip_metadata(self):
        text = "<!-- METADATA\ntitle: Test\n-->\n\n# Article content"
        result = AIRewrite._strip_metadata(text)
        assert "# Article content" in result
        assert "METADATA" not in result


class TestSeoMetadata:
    def test_component_name(self):
        comp = SeoMetadataComp()
        assert comp.name == "seo_metadata"

    def test_truncate_title_short(self):
        result = SeoMetadataComp._truncate_title("Hello World", "TestSite")
        assert "Hello World" in result

    def test_truncate_title_long(self):
        long = "A" * 70
        result = SeoMetadataComp._truncate_title(long, "Site")
        assert len(result) <= 65

    def test_truncate_title_with_suffix(self):
        title = "A" * 50 + " | Site"
        result = SeoMetadataComp._truncate_title(title, "Site")
        assert " | Site" in result


class TestHtmlRender:
    def test_component_name(self):
        comp = HtmlRender()
        assert comp.name == "html_render"

    def test_required_fields(self):
        comp = HtmlRender()
        assert "article_md" in comp.required_fields

    def test_parse_sections(self):
        comp = HtmlRender()
        md = """## Introduction
Hello world.

## Step 1: Setup
Do this.

## FAQ: What is this?
Answer here.
"""
        sections, faq = comp._parse_sections(md)
        assert len(sections) >= 2
        assert len(faq) >= 1
        assert "What is this?" in faq[0]["question"]

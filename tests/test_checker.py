"""Tests for content checker."""
import pytest
from ytarticle.core.schema import ContentItem, make_item, SeoMetadata
from ytarticle.components.checkers.content_check import ContentCheck


class TestContentCheck:
    def test_component_name(self):
        comp = ContentCheck()
        assert comp.name == "content_check"

    def test_short_article_triggers_warning(self):
        comp = ContentCheck()
        item = make_item("youtube", "123", title="Short")
        item.seo = SeoMetadata(title_tag="Short")
        item.article_md = "Hello"
        result = comp.run(item, {})
        warnings = result.source_metadata.get("check_warnings", [])
        assert any("too short" in w for w in warnings)

    def test_good_article_no_warnings(self):
        comp = ContentCheck()
        item = make_item("youtube", "123", title="Good DIY Project")
        item.seo = SeoMetadata(title_tag="Good DIY Project | Site", meta_description="A desc")
        item.article_md = "Word " * 150
        item.difficulty = "easy"
        result = comp.run(item, {})
        warnings = result.source_metadata.get("check_warnings", [])
        assert len(warnings) == 0

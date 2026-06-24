"""Tests for base component and registry."""
import pytest
from ytarticle.core.base import BaseComponent, ComponentError
from ytarticle.core.registry import Registry
from ytarticle.core.schema import ContentItem, make_item


class TestBaseComponent:
    def test_validate_input_missing(self):
        comp = _make_dummy()
        item = ContentItem()
        missing = comp.validate_input(item)
        assert "title" in missing

    def test_validate_input_ok(self):
        comp = _make_dummy()
        item = make_item("youtube", "123", title="Hello")
        missing = comp.validate_input(item)
        assert missing == []

    def test_run(self):
        comp = _make_dummy()
        item = make_item("youtube", "123", title="Test")
        result = comp.run(item, {})
        assert result.article_md == "# Test"


class TestRegistry:
    def test_register_and_get(self):
        reg = Registry()
        comp = _make_dummy()
        reg.register(comp)
        assert reg.has("dummy")
        assert reg.get("dummy") is comp

    def test_list_all(self):
        reg = Registry()
        reg.register(_make_dummy())
        assert "dummy" in reg.list_all()

    def test_get_missing_raises(self):
        reg = Registry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")


def _make_dummy():
    class Dummy(BaseComponent):
        name = "dummy"
        version = "1.0.0"
        required_fields = ["title"]
        output_fields = ["article_md"]

        def run(self, item, config):
            item.article_md = f"# {item.title}"
            return item
    return Dummy()

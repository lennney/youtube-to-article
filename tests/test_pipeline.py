"""Tests for pipeline engine."""
import tempfile
from pathlib import Path
import yaml

import pytest
from ytarticle.core.pipeline import Pipeline
from ytarticle.core.schema import ContentItem, make_item
from ytarticle.core.base import BaseComponent


class UppercaseTitle(BaseComponent):
    name = "uppercase_title"
    version = "1.0.0"
    required_fields = ["title"]

    def run(self, item, config):
        item.article_md = item.title.upper()
        return item


class TestPipeline:
    def test_pipeline_with_components(self, dummy_comp):
        pipe = Pipeline({"steps": [{"component": "dummy"}]})
        pipe.registry.register(dummy_comp)
        item = make_item("youtube", "123", title="Hello")
        result = pipe.run(item)
        assert result.status == "done"
        assert result.article_md == "# Hello"

    def test_pipeline_component_not_found(self):
        pipe = Pipeline({"steps": [{"component": "nonexistent"}]})
        item = make_item("youtube", "123")
        result = pipe.run(item)
        assert result.status == "failed"
        assert "not found" in result.error

    def test_pipeline_missing_input(self, dummy_comp):
        pipe = Pipeline({"steps": [{"component": "dummy"}]})
        pipe.registry.register(dummy_comp)
        item = ContentItem()
        result = pipe.run(item)
        assert result.status == "failed"
        assert "missing" in result.error

    def test_pipeline_yaml_config(self):
        config_yaml = """
steps:
  - component: uppercase_title
    id: step1
"""
        config = yaml.safe_load(config_yaml)
        pipe = Pipeline(config)
        pipe.registry.register(UppercaseTitle())
        item = make_item("youtube", "123", title="hello")
        result = pipe.run(item)
        assert result.status == "done"
        assert result.article_md == "HELLO"

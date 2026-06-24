"""Shared test fixtures and helpers."""
import pytest
from ytarticle.core.base import BaseComponent
from ytarticle.core.schema import ContentItem


class DummyComponent(BaseComponent):
    """A no-op component for pipeline testing."""
    name = "dummy"
    version = "1.0.0"
    required_fields = ["title"]
    output_fields = ["article_md"]

    def run(self, item: ContentItem, config: dict) -> ContentItem:
        item.article_md = f"# {item.title}"
        return item


@pytest.fixture
def dummy_comp():
    return DummyComponent()

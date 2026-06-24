"""Content quality checker."""
from __future__ import annotations
import logging
from typing import Any

from ytarticle.core.base import BaseComponent
from ytarticle.core.schema import ContentItem

logger = logging.getLogger("ytarticle.content_check")


class ContentCheck(BaseComponent):
    name = "content_check"
    version = "1.0.0"
    required_fields = ["article_md", "seo"]
    output_fields: list[str] = []

    CHECK_TITLE_MIN = 10
    CHECK_TITLE_MAX = 120
    CHECK_DESC_MAX = 160
    CHECK_BODY_MIN_WORDS = 100

    def run(self, item: ContentItem, config: dict[str, Any]) -> ContentItem:
        warnings = []

        word_count = len(item.article_md.split())
        if word_count < self.CHECK_BODY_MIN_WORDS:
            warnings.append(f"Article too short: {word_count} words (min {self.CHECK_BODY_MIN_WORDS})")

        title = item.seo.title_tag or item.title
        if len(title) < self.CHECK_TITLE_MIN:
            warnings.append(f"Title too short: {len(title)} chars")
        if len(title) > self.CHECK_TITLE_MAX:
            warnings.append(f"Title too long: {len(title)} chars (max {self.CHECK_TITLE_MAX})")

        if item.seo.meta_description:
            if len(item.seo.meta_description) > self.CHECK_DESC_MAX:
                warnings.append(f"Description too long: {len(item.seo.meta_description)} chars")

        if item.difficulty not in ("easy", "medium", "hard"):
            warnings.append(f"Unknown difficulty: {item.difficulty}")

        if warnings:
            for w in warnings:
                logger.warning(f"[content_check] {w}")
        else:
            logger.info("[content_check] All checks passed")

        item.source_metadata["check_warnings"] = warnings
        return item


def create():
    return ContentCheck()

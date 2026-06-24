"""Tests for schema module."""
import pytest
from ytarticle.core.schema import ContentItem, Source, make_item, ImageInfo


class TestContentItem:
    def test_default_creation(self):
        item = ContentItem()
        assert item.status == "pending"
        assert item.source == Source.YOUTUBE

    def test_make_item_with_source_id(self):
        item = make_item("youtube", "abc123", title="Test Video")
        assert item.source_id == "abc123"
        assert item.title == "Test Video"
        assert item.task_id() == "youtube_abc123"

    def test_mark_running_sets_timestamp(self):
        item = ContentItem()
        item.mark_running()
        assert item.status == "running"
        assert item.started_at != ""

    def test_mark_done(self):
        item = ContentItem()
        item.mark_done()
        assert item.status == "done"
        assert item.completed_at != ""

    def test_mark_failed(self):
        item = ContentItem()
        item.mark_failed("Something broke")
        assert item.status == "failed"
        assert "Something broke" in item.error

    def test_image_info_defaults(self):
        img = ImageInfo()
        assert img.path == ""
        assert img.step == 0

    def test_artifact_paths_includes_cover_img(self):
        from ytarticle.core.schema import ArtifactPaths
        ap = ArtifactPaths()
        assert hasattr(ap, "cover_img")
        assert ap.cover_img == ""

    def test_seo_metadata_no_meta_keywords(self):
        from ytarticle.core.schema import SeoMetadata
        seo = SeoMetadata()
        assert not hasattr(seo, "meta_keywords")

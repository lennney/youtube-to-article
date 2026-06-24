"""Tests for YouTube components."""
import pytest
from ytarticle.components.sources.youtube_extract import YouTubeExtract


class TestYouTubeExtractComponent:
    def test_component_name_and_version(self):
        comp = YouTubeExtract()
        assert comp.name == "youtube_extract"
        assert comp.version == "1.0.0"

    def test_required_fields(self):
        comp = YouTubeExtract()
        assert "source_id" in comp.required_fields

    def test_create_function(self):
        from ytarticle.components.sources.youtube_extract import create
        comp = create()
        assert comp.name == "youtube_extract"

    def test_srt_to_text(self):
        srt = """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
How are you
"""
        text = YouTubeExtract._srt_to_text(srt)
        assert "Hello world" in text
        assert "How are you" in text
        assert "--> " not in text

    def test_parse_timed(self):
        vtt = """WEBVTT
00:00:01.000 --> 00:00:04.000
Hello world

00:00:05.000 --> 00:00:08.000
How are you
"""
        segments = YouTubeExtract._parse_timed(vtt)
        assert len(segments) == 2
        assert segments[0]["text"] == "Hello world"
        assert segments[1]["start"] == "00:00:05.000"

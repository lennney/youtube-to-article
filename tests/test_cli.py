"""Tests for CLI."""
from click.testing import CliRunner
from ytarticle.cli import cli, _extract_video_id


class TestVideoIdExtraction:
    def test_standard_url(self):
        assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert _extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert _extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert _extract_video_id("https://example.com") is None

    def test_with_params(self):
        assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s") == "dQw4w9WgXcQ"


class TestCLI:
    def test_templates_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["templates"])
        assert result.exit_code == 0
        assert "default" in result.output
        assert "diyhub" in result.output

    def test_run_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--url" in result.output

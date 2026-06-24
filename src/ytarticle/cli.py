"""CLI — AI agent entry point for youtube-to-article pipeline."""
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from ytarticle.core.schema import ContentItem, make_item
from ytarticle.core.pipeline import Pipeline


@click.group()
@click.option("--verbose", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, verbose: bool):
    """youtube-to-article — YouTube video → DIY article pipeline."""
    ctx.ensure_object(dict)
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    ctx.obj["logger"] = logging.getLogger("cli")


@cli.command()
@click.option("--url", required=True, help="YouTube video URL")
@click.option("--cookies", help="Path to Netscape cookies file")
@click.option("--proxy", help="HTTP proxy (e.g. http://127.0.0.1:8080)")
@click.option("--output-dir", default="output", help="Output directory")
@click.option("--template", default="diyhub", help="HTML template name")
@click.option("--site-name", default="MakeDIYHub", help="Site name for SEO")
@click.option("--site-url", default="https://makediyhub.com", help="Site URL")
@click.option("--json", "json_output", is_flag=True, help="Output JSON result to stdout")
@click.pass_context
def run(ctx, url: str, cookies: Optional[str], proxy: Optional[str],
        output_dir: str, template: str, site_name: str, site_url: str,
        json_output: bool):
    """Run full pipeline on a single YouTube URL."""
    logger = ctx.obj["logger"]

    video_id = _extract_video_id(url)
    if not video_id:
        click.echo("Error: Could not extract video ID from URL", err=True)
        sys.exit(1)

    config = {
        "steps": [
            {"component": "youtube_extract",
             "id": "extract",
             "config": {"output_dir": f"{output_dir}/raw", "cookies_path": cookies or "",
                        "proxy_http": proxy or ""}},
            {"component": "ai_rewrite", "id": "rewrite"},
            {"component": "youtube_frames",
             "id": "frames",
             "config": {"output_dir": f"{output_dir}/images", "cookies_path": cookies or "",
                        "proxy_http": proxy or ""}},
            {"component": "seo_metadata", "id": "seo",
             "config": {"site_name": site_name}},
            {"component": "html_render", "id": "render",
             "config": {"output_dir": f"{output_dir}/html",
                        "template": f"{template}/article.html",
                        "site_url": site_url, "site_name": site_name,
                        "template_dirs": ["templates"]}},
            {"component": "content_check", "id": "check"},
        ]
    }

    item = make_item("youtube", video_id, source_url=url, keyword=site_name)

    pipeline = Pipeline(config)
    result = pipeline.run(item)

    if result.status == "failed":
        click.echo(f"Pipeline failed: {result.error}", err=True)
        sys.exit(1)

    click.echo(f"✅ Article created: {result.artifacts.html_path}")
    click.echo(f"   Title: {result.title}")
    click.echo(f"   Words: {len(result.article_md.split())}")

    if json_output:
        click.echo(json.dumps({
            "status": result.status,
            "title": result.title,
            "html_path": result.artifacts.html_path,
            "article_path": result.artifacts.article_md,
            "word_count": len(result.article_md.split()),
            "difficulty": result.difficulty,
            "images": len(result.images),
        }, indent=2))


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r"(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


@cli.command()
def templates():
    """List available templates."""
    from ytarticle.templates.base import list_templates
    for t in list_templates():
        click.echo(t)


if __name__ == "__main__":
    cli()

"""CLI — AI agent entry point for youtube-to-article pipeline.
Supports --config for full customization. All defaults work without a config file.
"""
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from ytarticle.core.schema import make_item
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
@click.option("--config", "config_path", default="configs/default.yaml",
              help="Pipeline config YAML path (default: configs/default.yaml)")
@click.option("--json", "json_output", is_flag=True, help="Output JSON result to stdout")
@click.pass_context
def run(ctx, url: str, cookies: Optional[str], proxy: Optional[str],
        output_dir: str, template: str, site_name: str, site_url: str,
        config_path: str, json_output: bool):
    """Run full pipeline on a single YouTube URL.

    Examples:

    \b
      # Quick run (uses configs/default.yaml)
      ytarticle run --url "https://youtube.com/watch?v=xxx"
    
    \b
      # With custom config
      ytarticle run --url "..." --config myconfig.yaml
    
    \b
      # All overrides merged into config
      ytarticle run --url "..." --cookies cookies.txt --template default
    """
    logger = ctx.obj["logger"]

    video_id = _extract_video_id(url)
    if not video_id:
        click.echo("Error: Could not extract video ID from URL", err=True)
        sys.exit(1)

    # Build base config from file (or default)
    config = _build_config(config_path, {
        "output_dir": output_dir,
        "cookies": cookies or "",
        "proxy": proxy or "",
        "template": template,
        "site_name": site_name,
        "site_url": site_url,
    })

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


def _build_config(config_path: str, overrides: dict) -> dict:
    """Load config from YAML and merge CLI overrides.

    The config file defines pipeline steps. CLI overrides are merged into
    each step's config (e.g., cookies, proxy, output_dir).
    """
    import yaml

    # Load from file or use default inline config
    p = Path(config_path)
    if p.exists():
        config = yaml.safe_load(p.read_text(encoding="utf-8"))
    else:
        # Inline default (backward compatible when config file not found)
        config = {"steps": [
            {"component": "youtube_extract", "id": "extract",
             "config": {"output_dir": f"{overrides['output_dir']}/raw"}},
            {"component": "ai_rewrite", "id": "rewrite",
             "config": {"prompt_file": "prompts/rewrite_article.md"}},
            {"component": "youtube_frames", "id": "frames",
             "config": {"output_dir": f"{overrides['output_dir']}/images"}},
            {"component": "seo_metadata", "id": "seo",
             "config": {"prompt_file": "prompts/seo_metadata.md",
                       "site_name": overrides["site_name"]}},
            {"component": "html_render", "id": "render",
             "config": {"output_dir": f"{overrides['output_dir']}/html",
                       "template": f"{overrides['template']}/article.html",
                       "site_url": overrides["site_url"],
                       "site_name": overrides["site_name"]}},
            {"component": "content_check", "id": "check", "config": {}},
        ]}

    # Merge CLI overrides into step configs
    cookies = overrides.get("cookies", "")
    proxy = overrides.get("proxy", "")

    for step in config.get("steps", []):
        scfg = step.setdefault("config", {})
        step_id = step.get("id", "")
        out = overrides["output_dir"]

        if step_id == "extract":
            scfg.setdefault("output_dir", f"{out}/raw")
            if cookies:
                scfg["cookies_path"] = cookies
            if proxy:
                scfg["proxy_http"] = proxy
        elif step_id == "frames":
            scfg.setdefault("output_dir", f"{out}/images")
            if cookies:
                scfg["cookies_path"] = cookies
            if proxy:
                scfg["proxy_http"] = proxy
        elif step_id == "seo":
            scfg.setdefault("site_name", overrides["site_name"])
        elif step_id == "render":
            scfg.setdefault("output_dir", f"{out}/html")
            scfg.setdefault("template", f"{overrides['template']}/article.html")
            scfg.setdefault("site_url", overrides["site_url"])
            scfg.setdefault("site_name", overrides["site_name"])

    return config


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

"""HTML render component — pluggable template rendering."""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader
import markdown as md_lib

from ytarticle.core.base import BaseComponent
from ytarticle.core.schema import ContentItem
from ytarticle.templates.base import resolve_template

logger = logging.getLogger("ytarticle.html_render")


class HtmlRender(BaseComponent):
    name = "html_render"
    version = "1.0.0"
    required_fields = ["article_md", "seo"]
    output_fields = ["artifacts.html_path"]

    def __init__(self):
        super().__init__()
        self._env: Optional[Environment] = None

    def _get_env(self, template_dir: Path) -> Environment:
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=False,
            )
        return self._env

    def _parse_sections(self, md: str) -> tuple[list[dict], list[dict]]:
        sections = []
        faq = []
        current = None
        current_lines = []

        for line in md.split("\n"):
            if line.startswith("## "):
                if current:
                    current["body"] = md_lib.markdown("\n".join(current_lines))
                    sections.append(current)
                heading = line[3:].strip()
                current = {"heading": heading, "body": ""}
                current_lines = []
            elif line.startswith("### "):
                if current:
                    current["body"] = md_lib.markdown("\n".join(current_lines))
                    sections.append(current)
                current = {"heading": line[4:].strip(), "body": ""}
                current_lines = []
            else:
                current_lines.append(line)

        if current:
            current["body"] = md_lib.markdown("\n".join(current_lines))
            sections.append(current)

        faq_sections = [s for s in sections if "faq" in s["heading"].lower()]
        sections = [s for s in sections if "faq" not in s["heading"].lower()]
        for fs in faq_sections:
            faq.append({"question": fs["heading"].replace("FAQ:", "").strip(), "answer": fs["body"]})

        return sections, faq

    def run(self, item: ContentItem, config: dict[str, Any]) -> ContentItem:
        template_name = config.get("template", "default/article.html")
        custom_dirs = config.get("template_dirs", [])

        template_dir, resolved_name = resolve_template(template_name, custom_dirs=custom_dirs)
        env = self._get_env(template_dir)
        template = env.get_template(resolved_name)

        sections, faq = self._parse_sections(item.article_md)

        site_url = config.get("site_url", "https://example.com")
        url_slug = item.seo.url_slug or f"/diy/{item.source_id}"

        howto_schema = self._build_howto_schema(item, sections, site_url, url_slug)
        article_schema = self._build_article_schema(item, site_url, url_slug)
        breadcrumb_schema = self._build_breadcrumb_schema(url_slug)
        faq_schema = self._build_faq_schema(faq, site_url, url_slug) if faq else None

        step_imgs = {}
        for img in item.images:
            if img.step > 0 and img.path:
                step_imgs[img.step] = img.path

        html = template.render(
            title_tag=item.seo.title_tag or item.title,
            meta_description=item.seo.meta_description,
            url_slug=url_slug,
            title=item.title,
            difficulty=item.difficulty,
            estimated_time=item.estimated_time,
            estimated_cost=item.estimated_cost,
            materials=item.materials,
            sections=sections,
            step_images=step_imgs,
            faq=faq,
            date_published=item.started_at or datetime.now().isoformat(),
            SITE_URL=site_url,
            SITE_NAME=config.get("site_name", "MakeDIYHub"),
            SITE_SLOGAN=config.get("site_slogan", ""),
            howto_schema_json=json.dumps(howto_schema, ensure_ascii=False),
            article_schema_json=json.dumps(article_schema, ensure_ascii=False),
            breadcrumb_schema_json=json.dumps(breadcrumb_schema, ensure_ascii=False),
            faq_schema_json=json.dumps(faq_schema, ensure_ascii=False) if faq_schema else None,
            cover_img=item.artifacts.cover_img or "",
            images=item.images,
        )

        output_dir = Path(config.get("output_dir", "output/html"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{item.source_id}.html"
        output_path.write_text(html, encoding="utf-8")
        item.artifacts.html_path = str(output_path)

        logger.info(f"[html_render] Wrote {output_path}")
        return item

    @staticmethod
    def _build_howto_schema(item: ContentItem, sections: list[dict],
                            site_url: str, url_slug: str) -> dict:
        steps = []
        for s in sections:
            if "step" in s["heading"].lower():
                steps.append({
                    "@type": "HowToStep",
                    "position": len(steps) + 1,
                    "name": s["heading"],
                    "text": s["body"],
                })
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": item.title,
            "description": item.seo.meta_description or "",
            "totalTime": item.estimated_time,
            "cost": item.estimated_cost,
            "step": steps,
        }
        if item.materials:
            schema["supply"] = [{"@type": "HowToSupply", "name": m} for m in item.materials]
        return schema

    @staticmethod
    def _build_article_schema(item: ContentItem, site_url: str, url_slug: str) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": item.title,
            "description": item.seo.meta_description or "",
            "author": {"@type": "Person", "name": item.author or "MakeDIYHub Team"},
            "datePublished": item.started_at or datetime.now().isoformat(),
        }

    @staticmethod
    def _build_breadcrumb_schema(url_slug: str) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "/"},
                {"@type": "ListItem", "position": 2, "name": "DIY", "item": url_slug},
            ],
        }

    @staticmethod
    def _build_faq_schema(faq: list[dict], site_url: str, url_slug: str) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["question"],
                 "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}}
                for f in faq
            ],
        }


def create():
    return HtmlRender()

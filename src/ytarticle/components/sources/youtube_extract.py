"""YouTube subtitle extraction via yt-dlp."""
from __future__ import annotations
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from ytarticle.core.base import BaseComponent, ComponentError
from ytarticle.core.schema import ContentItem
from ytarticle.support.cookies import CookieManager
from ytarticle.support.proxy import ProxyManager

logger = logging.getLogger("ytarticle.youtube_extract")


class YouTubeExtract(BaseComponent):
    name = "youtube_extract"
    version = "1.0.0"
    required_fields = ["source_id"]
    output_fields = ["title", "raw_text", "source_metadata"]

    def _download_metadata(self, video_id: str, cookies: CookieManager,
                           proxy: ProxyManager) -> dict:
        cmd = [sys.executable, "-m", "yt_dlp",
               "--dump-json", "--skip-download",
               "--no-warnings",
               *cookies.yt_dlp_args(),
               *proxy.yt_dlp_args(),
               "--impersonate", "chrome",
               f"https://www.youtube.com/watch?v={video_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise ComponentError(f"yt-dlp metadata failed: {result.stderr[:200]}")
        return json.loads(result.stdout)

    def _download_transcript(self, video_id: str, output_dir: Path,
                             cookies: CookieManager, proxy: ProxyManager) -> tuple[str, str]:
        text_path = output_dir / f"{video_id}.txt"
        json_path = output_dir / f"{video_id}_timed.json"

        cmd = [sys.executable, "-m", "yt_dlp",
               "--skip-download",
               "--write-subs", "--write-auto-subs",
               "--sub-langs", "en,-live_chat",
               "--convert-subs", "srt",
               "--sub-format", "vtt/txt",
               "--no-warnings",
               *cookies.yt_dlp_args(),
               *proxy.yt_dlp_args(),
               "--impersonate", "chrome",
               "-o", str(output_dir / f"{video_id}.%(ext)s"),
               f"https://www.youtube.com/watch?v={video_id}"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        raw_text = ""
        timed_data = []

        for ext in [".en.vtt", ".en.srt", ".vtt", ".srt"]:
            sub_path = output_dir / f"{video_id}{ext}"
            if sub_path.exists():
                raw_text = self._srt_to_text(sub_path.read_text(encoding="utf-8"))
                timed_data = self._parse_timed(sub_path.read_text(encoding="utf-8"))
                break

        if raw_text:
            text_path.write_text(raw_text, encoding="utf-8")
        if timed_data:
            json_path.write_text(json.dumps(timed_data, ensure_ascii=False), encoding="utf-8")

        return str(text_path), str(json_path) if timed_data else ""

    @staticmethod
    def _srt_to_text(srt_content: str) -> str:
        lines = []
        for line in srt_content.split("\n"):
            line = line.strip()
            if (not line or "-->" in line or line.isdigit()
                    or line.startswith("WEBVTT") or line.startswith("Kind:")
                    or line.startswith("Language:")):
                continue
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _parse_timed(content: str) -> list[dict]:
        segments = []
        current = {}
        for line in content.split("\n"):
            line = line.strip()
            if "-->" in line:
                parts = line.split("-->")
                if len(parts) == 2:
                    current = {"start": parts[0].strip(), "end": parts[1].strip(), "text": ""}
            elif line and current:
                if current["text"]:
                    current["text"] += " " + re.sub(r'<[^>]+>', '', line)
                else:
                    current["text"] = re.sub(r'<[^>]+>', '', line)
            elif not line and current.get("text"):
                segments.append(current)
                current = {}
        if current.get("text"):
            segments.append(current)
        return segments

    def run(self, item: ContentItem, config: dict[str, Any]) -> ContentItem:
        video_id = item.source_id
        output_dir = Path(config.get("output_dir", "output/raw"))

        cookies = CookieManager(config.get("cookies_path"))
        proxy = ProxyManager(http=config.get("proxy_http"))

        meta = self._download_metadata(video_id, cookies, proxy)
        item.title = meta.get("title", "")
        item.source_metadata = {
            "author": meta.get("uploader", ""),
            "channel": meta.get("uploader", ""),
            "published_at": meta.get("upload_date", ""),
            "duration": meta.get("duration", 0),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "view_count": meta.get("view_count", 0),
            "description": (meta.get("description", "") or "")[:500],
        }

        text_path, json_path = self._download_transcript(video_id, output_dir, cookies, proxy)
        if text_path:
            item.raw_text = Path(text_path).read_text(encoding="utf-8")
        item.artifacts.raw_text = text_path
        item.artifacts.timed_transcript = json_path

        logger.info(f"[youtube_extract] '{item.title}' — {len(item.raw_text)} chars transcript")
        return item


def create():
    return YouTubeExtract()

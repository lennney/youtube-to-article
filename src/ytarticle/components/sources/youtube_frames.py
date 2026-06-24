"""YouTube keyframe extraction via yt-dlp + ffmpeg."""
from __future__ import annotations
import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from ytarticle.core.base import BaseComponent
from ytarticle.core.schema import ContentItem, ImageInfo
from ytarticle.support.cookies import CookieManager
from ytarticle.support.proxy import ProxyManager
from ytarticle.support.llm import call_llm

logger = logging.getLogger("ytarticle.youtube_frames")


class YouTubeFrames(BaseComponent):
    name = "youtube_frames"
    version = "1.0.0"
    required_fields = ["source_id", "article_md"]
    output_fields = ["images"]

    def run(self, item: ContentItem, config: dict[str, Any]) -> ContentItem:
        if item.source.value != "youtube" or not item.source_id:
            return item

        if not shutil.which("ffmpeg"):
            logger.warning("[youtube_frames] ffmpeg not found — skipping")
            return item

        video_id = item.source_id
        output_dir = Path(config.get("output_dir", "output/images")) / video_id
        output_dir.mkdir(parents=True, exist_ok=True)

        cookies = CookieManager(config.get("cookies_path"))
        proxy = ProxyManager(http=config.get("proxy_http"))

        timestamps = self._detect_timestamps(item.article_md, item.artifacts.timed_transcript)
        video_path = self._download_video(video_id, output_dir, cookies, proxy)

        if not video_path:
            return item

        if timestamps:
            frames = self._extract_frames(video_path, timestamps, output_dir)
        else:
            fallback_count = len(re.findall(r"^## Step \d", item.article_md, re.MULTILINE)) or 8
            frames = self._fallback_frames(video_path, fallback_count, output_dir)

        video_path.unlink(missing_ok=True)

        for f in frames:
            item.images.append(ImageInfo(
                path=f["path"],
                alt=f.get("alt", f"Step {f['step']}"),
                step=f["step"],
            ))

        item.artifacts.images_dir = str(output_dir)
        return item

    def _detect_timestamps(self, article_md: str, timed_path: str) -> list[dict]:
        if not timed_path or not Path(timed_path).exists():
            return []

        steps_section = ""
        in_steps = False
        for line in article_md.split("\n"):
            if re.match(r"^##\s*Step", line, re.IGNORECASE):
                in_steps = True
            if in_steps and line.startswith("## ") and "Step" not in line:
                break
            if in_steps:
                steps_section += line + "\n"
        if not steps_section.strip():
            return []

        try:
            timed_data = json.loads(Path(timed_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        timed_sample = timed_data[::3][:80]
        system_prompt = (
            "You are a video timestamp detector. Given article steps and transcript "
            "segments with timestamps, output a JSON array of objects with 'step' (int), "
            "'timestamp' (HH:MM:SS), and 'label' (str) fields. "
            "Match each article step to the most relevant transcript timestamp. "
            "Output ONLY the JSON array."
        )
        user_prompt = f"Article steps:\n{steps_section.strip()}\n\nTranscript segments:\n{json.dumps(timed_sample, ensure_ascii=False)}"

        try:
            result = call_llm(system_prompt, user_prompt, max_tokens=2048, temperature=0.3)
            json_match = re.search(r"\[.*\]", result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"[youtube_frames] Timestamp detection failed: {e}")
        return []

    def _download_video(self, video_id: str, output_dir: Path,
                        cookies: CookieManager, proxy: ProxyManager) -> Path | None:
        video_path = output_dir / f"{video_id}.mp4"
        if video_path.exists():
            return video_path

        cmd = [sys.executable, "-m", "yt_dlp",
               "-f", "bestvideo[height<=480]",
               *cookies.yt_dlp_args(),
               *proxy.yt_dlp_args(),
               "--impersonate", "chrome",
               "-o", str(video_path),
               f"https://www.youtube.com/watch?v={video_id}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            logger.warning(f"[youtube_frames] Download timed out for {video_id}")
            return None
        except OSError as e:
            logger.warning(f"[youtube_frames] Download error: {e}")
            return None

        if result.returncode != 0 or not video_path.exists():
            logger.warning(f"[youtube_frames] Download failed: {result.stderr[:200]}")
            return None
        return video_path

    def _extract_frames(self, video_path: Path, timestamps: list[dict],
                        output_dir: Path) -> list[dict]:
        ts_pattern = re.compile(r"^\d{2}:\d{2}:\d{2}$")
        frames = []
        for item in timestamps:
            ts = item.get("timestamp", "")
            if not ts_pattern.match(ts):
                continue
            step = item.get("step", len(frames) + 1)
            frame_path = output_dir / f"step_{step:02d}.jpg"
            try:
                result = subprocess.run(
                    ["ffmpeg", "-ss", ts, "-i", str(video_path),
                     "-frames:v", "1", "-q:v", "2",
                     "-filter:v", "scale=800:-1",
                     "-y", str(frame_path)],
                    capture_output=True, text=True, timeout=30)
            except (FileNotFoundError, OSError):
                continue
            if result.returncode == 0 and frame_path.exists():
                frames.append({"path": str(frame_path),
                              "alt": item.get("label", f"Step {step}"),
                              "step": step})
        return frames

    def _fallback_frames(self, video_path: Path, num_steps: int,
                         output_dir: Path) -> list[dict]:
        if not shutil.which("ffprobe"):
            return []
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "json", str(video_path)],
            capture_output=True, text=True, timeout=15)
        try:
            duration = float(json.loads(result.stdout).get("format", {}).get("duration", 600))
        except (json.JSONDecodeError, KeyError, ValueError):
            duration = 600

        interval = duration / (num_steps + 1)
        frames = []
        for i in range(1, num_steps + 1):
            t = int(interval * i)
            mm, ss = divmod(t, 60)
            hh, mm = divmod(mm, 60)
            ts = f"{hh:02d}:{mm:02d}:{ss:02d}"
            frame_path = output_dir / f"step_{i:02d}.jpg"
            try:
                result = subprocess.run(
                    ["ffmpeg", "-ss", ts, "-i", str(video_path),
                     "-frames:v", "1", "-q:v", "2",
                     "-filter:v", "scale=800:-1",
                     "-y", str(frame_path)],
                    capture_output=True, text=True, timeout=30)
            except (FileNotFoundError, OSError):
                continue
            if result.returncode == 0 and frame_path.exists():
                frames.append({"path": str(frame_path), "alt": f"Step {i}", "step": i})
        return frames


def create():
    return YouTubeFrames()

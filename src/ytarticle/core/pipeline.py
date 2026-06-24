"""Pipeline engine — config-driven step orchestrator."""
from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Any

import yaml

from ytarticle.core.schema import ContentItem
from ytarticle.core.base import ComponentError
from ytarticle.core.registry import Registry

logger = logging.getLogger("ytarticle.pipeline")


class Pipeline:
    """Config-driven content pipeline."""

    def __init__(self, config: dict[str, Any] | str | Path):
        if isinstance(config, (str, Path)):
            config = self._load_config(config)
        self.config = config
        self.steps = config.get("steps", [])
        self.max_retries = config.get("max_retries", 2)
        self.registry = Registry()
        self.registry.discover()

    @staticmethod
    def _load_config(path: str | Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run(self, item: ContentItem) -> ContentItem:
        """Run all configured steps."""
        item.mark_running()
        task_id = item.task_id()

        for step_idx, step_conf in enumerate(self.steps):
            comp_name = step_conf.get("component", "")
            comp_config = step_conf.get("config", {})
            step_name = step_conf.get("id", comp_name)

            if not self.registry.has(comp_name):
                item.mark_failed(f"Component '{comp_name}' not found")
                return item

            comp = self.registry.get(comp_name)

            missing = comp.validate_input(item)
            if missing:
                item.mark_failed(f"{comp_name}: missing {missing}")
                return item

            success = False
            last_error = ""
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info(f"[pipeline] Running: {comp_name}"
                                + (f" (attempt {attempt+1})" if attempt > 0 else ""))
                    item = comp.run(item, comp_config)
                    success = True
                    break
                except ComponentError as e:
                    last_error = str(e)
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    logger.warning(f"[pipeline] {comp_name} error: {e}")
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)

            if not success:
                item.mark_failed(f"{comp_name}: {last_error}")
                return item

            logger.info(f"[pipeline] {comp_name} done")

        item.mark_done()
        logger.info(f"[pipeline] Done: {task_id}")
        return item


def run_from_config(config_path: str, item: ContentItem) -> ContentItem:
    """Convenience: one-liner to run a pipeline."""
    pipe = Pipeline(config_path)
    return pipe.run(item)

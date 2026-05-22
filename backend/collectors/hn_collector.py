from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.collectors.base import BaseCollector
from backend.core.config import AppConfig, get_config

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class HNCollector(BaseCollector[dict]):
    source_name = "hn"

    def _get_source_config(self, config: AppConfig):
        return config.hackernews

    def collect(
        self,
        story_type: str = "top",
        max_stories: int | None = None,
    ) -> list[dict]:
        config = self._get_source_config(get_config())
        max_stories = max_stories or config.max_stories_per_fetch

        endpoint = f"{HN_API_BASE}/{story_type}stories.json"
        response = self._fetch_with_retry(endpoint)
        story_ids = response.json()[:max_stories]

        results = []
        for hn_id in story_ids:
            item_url = f"{HN_API_BASE}/item/{hn_id}.json"
            try:
                item_resp = self._fetch_with_retry(item_url)
                item = item_resp.json()
                if item and item.get("type") == "story":
                    results.append(self._item_to_dict(item))
            except Exception as e:
                logger.warning("[hn] Failed to fetch item %d: %s", hn_id, e)
                continue

        logger.info("[hn] Collected %d stories", len(results))
        return results

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        stories = self.collect(**kwargs)
        since_ts = since.timestamp()
        return [s for s in stories if s["time_published"].timestamp() >= since_ts]

    @staticmethod
    def _item_to_dict(item: dict) -> dict:
        ts = item.get("time", 0)
        return {
            "hn_id": item["id"],
            "item_type": item.get("type", "story"),
            "title": item.get("title", ""),
            "url": item.get("url"),
            "text": item.get("text"),
            "score": item.get("score", 0),
            "author": item.get("by"),
            "descendants": item.get("descendants", 0),
            "time_published": datetime.fromtimestamp(ts, tz=timezone.utc),
            "fetched_at": datetime.now(timezone.utc),
        }

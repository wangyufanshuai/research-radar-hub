from __future__ import annotations

import logging
from datetime import datetime, timezone

from dateutil import parser as date_parser

from backend.collectors.base import BaseCollector
from backend.collectors.html_utils import absolute_url, content_hash, normalize_text, parse_html
from backend.core.config import AppConfig, SchoolNoticeSource, get_config

logger = logging.getLogger(__name__)


class SchoolNoticeCollector(BaseCollector[dict]):
    source_name = "school"

    def _get_source_config(self, config: AppConfig):
        return config.school_notices

    def collect(self, **kwargs) -> list[dict]:
        config = get_config().school_notices
        if not config.enabled:
            return []

        results: list[dict] = []
        for source in config.sources:
            try:
                results.extend(self._collect_source(source))
            except Exception as exc:
                logger.warning("[school] Failed to collect %s: %s", source.url, exc)
        return results

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        items = self.collect(**kwargs)
        return [
            item for item in items
            if item["published_at"] is None or item["published_at"] >= since
        ]

    def _collect_source(self, source: SchoolNoticeSource) -> list[dict]:
        self.robots_required = source.robots_required
        response = self._fetch_with_retry(source.url)
        soup = parse_html(response.text)
        nodes = soup.select(source.selector or "a")
        now = datetime.now(timezone.utc)
        results: list[dict] = []

        for node in nodes:
            title = normalize_text(node.get_text(" "))
            if not title:
                continue
            href = node.get("href") if hasattr(node, "get") else None
            url = absolute_url(source.url, href) or source.url
            if source.keywords and not any(keyword in title for keyword in source.keywords):
                continue
            published_at = self._extract_date(node.get_text(" "))
            digest = content_hash(source.id, title, url)
            results.append(
                {
                    "source_id": source.id,
                    "source_name": source.name,
                    "title": title,
                    "url": url,
                    "published_at": published_at,
                    "summary": title[:500],
                    "content_hash": digest,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "is_active": True,
                }
            )

        return results

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        try:
            parsed = date_parser.parse(text, fuzzy=True)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            return None

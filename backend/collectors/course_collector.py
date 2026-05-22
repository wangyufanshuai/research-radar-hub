from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import feedparser
from dateutil import parser as date_parser

from backend.collectors.base import BaseCollector
from backend.collectors.html_utils import absolute_url, content_hash, normalize_text, parse_html
from backend.core.config import AppConfig, CourseSourceConfig, get_config

logger = logging.getLogger(__name__)


class CourseCollector(BaseCollector[dict]):
    source_name = "course"

    def _get_source_config(self, config: AppConfig):
        return config.course_radar

    def collect(self, **kwargs) -> list[dict]:
        config = get_config().course_radar
        if not config.enabled:
            return []

        results: list[dict] = []
        for source in config.sources:
            if not source.enabled:
                continue
            try:
                if source.kind == "rss":
                    results.extend(self._collect_rss(source))
                else:
                    results.extend(self._collect_html(source))
            except Exception as exc:
                logger.warning("[course] Failed to collect %s: %s", source.url, exc)
        return results

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        items = self.collect(**kwargs)
        return [
            item
            for item in items
            if (item["published_at"] or item["first_seen_at"]) >= since
        ]

    def _collect_rss(self, source: CourseSourceConfig) -> list[dict]:
        self.robots_required = source.robots_required
        response = self._fetch_with_retry(source.url)
        feed = feedparser.parse(response.text)
        now = datetime.utcnow()
        results: list[dict] = []

        for entry in feed.entries:
            title = normalize_text(getattr(entry, "title", ""))
            if not title:
                continue
            url = normalize_text(getattr(entry, "link", "")) or source.url
            summary = normalize_text(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            if not self._matches_keywords(source, title, summary):
                continue
            published_at = self._entry_datetime(entry)
            results.append(self._item(source, title, url, summary, published_at, now))

        return results

    def _collect_html(self, source: CourseSourceConfig) -> list[dict]:
        self.robots_required = source.robots_required
        response = self._fetch_with_retry(source.url)
        soup = parse_html(response.text)
        nodes = soup.select(source.selector or "a")
        now = datetime.utcnow()
        results: list[dict] = []

        for node in nodes:
            link = node if getattr(node, "name", "") == "a" else node.select_one("a")
            title = normalize_text(node.get_text(" "))
            if not title:
                continue
            href = link.get("href") if link is not None and hasattr(link, "get") else None
            url = absolute_url(source.url, href) or source.url
            summary = title[:500]
            if not self._matches_keywords(source, title, summary):
                continue
            results.append(self._item(source, title, url, summary, None, now))

        return results

    @staticmethod
    def _matches_keywords(source: CourseSourceConfig, title: str, summary: str) -> bool:
        if not source.keywords:
            return True
        text = f"{title} {summary}".lower()
        return any(keyword.lower() in text for keyword in source.keywords)

    @staticmethod
    def _entry_datetime(entry) -> datetime | None:
        for attr in ("published", "updated", "created"):
            value = getattr(entry, attr, None)
            if not value:
                continue
            try:
                parsed = date_parser.parse(value)
                if parsed.tzinfo is None:
                    return parsed
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                continue
        return None

    @staticmethod
    def _item(
        source: CourseSourceConfig,
        title: str,
        url: str,
        summary: str,
        published_at: datetime | None,
        now: datetime,
    ) -> dict:
        topics = sorted(set(source.keywords))
        return {
            "institution": source.institution,
            "source_id": source.id,
            "title": title,
            "url": url,
            "summary": summary,
            "department": source.department,
            "level": source.level,
            "topics": json.dumps(topics, ensure_ascii=False),
            "published_at": published_at,
            "first_seen_at": now,
            "last_seen_at": now,
            "content_hash": content_hash(source.id, title, url, summary),
        }

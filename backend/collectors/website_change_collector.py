from __future__ import annotations

import difflib
import logging
from datetime import datetime, timezone

from backend.collectors.base import BaseCollector
from backend.collectors.html_utils import content_hash, extract_selected_text
from backend.core.config import AppConfig, WebsitePageConfig, get_config

logger = logging.getLogger(__name__)


class WebsiteChangeCollector(BaseCollector[dict]):
    source_name = "website"

    def _get_source_config(self, config: AppConfig):
        return config.website_changes

    def collect(self, **kwargs) -> list[dict]:
        config = get_config().website_changes
        if not config.enabled:
            return []

        pages = kwargs.get("pages") or config.pages
        results: list[dict] = []
        previous_hashes: dict[str, str | None] = kwargs.get("previous_hashes", {})
        previous_texts: dict[str, str | None] = kwargs.get("previous_texts", {})
        for page in pages:
            if not page.enabled:
                continue
            if page.render:
                logger.warning("[website] Skipping %s because Playwright rendering is not enabled in v1", page.url)
                continue
            try:
                item = self._collect_page(page, previous_hashes.get(page.url), previous_texts.get(page.url))
                if item:
                    results.append(item)
            except Exception as exc:
                logger.warning("[website] Failed to collect %s: %s", page.url, exc)
        return results

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        return self.collect(**kwargs)

    def _collect_page(
        self,
        page: WebsitePageConfig,
        previous_hash: str | None,
        previous_text: str | None,
    ) -> dict | None:
        self.robots_required = page.robots_required
        response = self._fetch_with_retry(page.url)
        title, text = extract_selected_text(response.text, page.selector)
        digest = content_hash(text)
        if previous_hash == digest:
            return None

        diff_summary = self._diff_summary(previous_text, text)
        now = datetime.now(timezone.utc)
        return {
            "page": {
                "name": page.name,
                "url": page.url,
                "selector": page.selector,
                "render": page.render,
                "enabled": page.enabled,
                "check_interval_minutes": page.check_interval_minutes,
                "robots_allowed": True,
                "last_checked_at": now,
                "last_status_code": response.status_code,
                "last_hash": digest,
            },
            "snapshot": {
                "content_hash": digest,
                "title": title,
                "text_excerpt": text[:1000],
                "diff_summary": diff_summary,
                "fetched_at": now,
                "status_code": response.status_code,
            },
        }

    @staticmethod
    def _diff_summary(previous_text: str | None, current_text: str) -> str:
        if not previous_text:
            return "Initial snapshot."
        previous_lines = previous_text.splitlines()
        current_lines = current_text.splitlines()
        diff = difflib.unified_diff(previous_lines, current_lines, lineterm="", n=2)
        return "\n".join(list(diff)[:40]) or "Content changed."

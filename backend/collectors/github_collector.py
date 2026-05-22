from __future__ import annotations

import json
import logging
from datetime import datetime

from backend.collectors.base import BaseCollector
from backend.core.config import AppConfig, get_config, get_secrets

logger = logging.getLogger(__name__)


class GitHubCollector(BaseCollector[dict]):
    source_name = "github"

    def _get_source_config(self, config: AppConfig):
        return config.github

    def _get_http_client(self):
        client = super()._get_http_client()
        secrets = get_secrets()
        if secrets.github_pat:
            client.headers["Authorization"] = f"Bearer {secrets.github_pat}"
        client.headers["Accept"] = "application/vnd.github+json"
        return client

    def collect(
        self,
        languages: list[str] | None = None,
        min_stars: int | None = None,
        query: str | None = None,
        max_results: int | None = None,
    ) -> list[dict]:
        config = get_config().github
        languages = languages or config.default_languages
        min_stars = min_stars or config.min_stars
        max_results = max_results or config.max_results_per_query

        results = []

        for lang in languages:
            if len(results) >= max_results:
                break
            q = f"language:{lang} stars:>={min_stars}"
            if query:
                q += f" {query}"

            per_page = max(1, min(100, max_results - len(results)))
            response = self._fetch_with_retry(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page},
            )
            for repo in response.json().get("items", []):
                results.append(self._repo_to_dict(repo))

        logger.info("[github] Collected %d repos", len(results))
        return results

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        date_str = since.strftime("%Y-%m-%d")
        query = kwargs.pop("query", None)
        incremental_query = f"pushed:>{date_str}"
        if query:
            incremental_query += f" {query}"
        return self.collect(query=incremental_query, **kwargs)

    @staticmethod
    def _repo_to_dict(repo) -> dict:
        raw_topics = repo.get("topics") or []
        license_info = repo.get("license") or {}
        return {
            "github_id": repo["id"],
            "full_name": repo["full_name"],
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count") or 0,
            "forks": repo.get("forks_count") or 0,
            "open_issues": repo.get("open_issues_count") or 0,
            "watchers": repo.get("watchers_count") or 0,
            "topics": json.dumps(raw_topics),
            "license_name": license_info.get("name"),
            "homepage": repo.get("homepage"),
            "html_url": repo.get("html_url"),
            "is_archived": bool(repo.get("archived")),
            "created_at_gh": GitHubCollector._parse_datetime(repo.get("created_at")),
            "updated_at_gh": GitHubCollector._parse_datetime(repo.get("updated_at")),
            "pushed_at_gh": GitHubCollector._parse_datetime(repo.get("pushed_at")),
            "fetched_at": datetime.utcnow(),
        }

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

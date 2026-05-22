from __future__ import annotations

import json
import logging
from datetime import datetime

import arxiv

from backend.collectors.base import BaseCollector
from backend.core.config import AppConfig, get_config

logger = logging.getLogger(__name__)


class ArxivCollector(BaseCollector[dict]):
    source_name = "arxiv"

    def _get_source_config(self, config: AppConfig):
        return config.arxiv

    def collect(
        self,
        categories: list[str] | None = None,
        query: str | None = None,
        max_results: int | None = None,
        sort_by: str = "submitted_date",
    ) -> list[dict]:
        config = get_config().arxiv
        categories = categories or config.default_categories
        max_results = max_results or config.max_results_per_query

        cat_query = " OR ".join(f"cat:{category}" for category in categories)
        search_query = f"({cat_query})"
        if query:
            search_query += f" AND ({query})"

        sort_map = {
            "submitted_date": arxiv.SortCriterion.SubmittedDate,
            "relevance": arxiv.SortCriterion.Relevance,
        }

        client = arxiv.Client(
            page_size=max(1, min(max_results, 25)),
            delay_seconds=config.rate_limit.request_delay_seconds,
            num_retries=config.retry.max_retries,
        )

        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=sort_map.get(sort_by, arxiv.SortCriterion.SubmittedDate),
            sort_order=arxiv.SortOrder.Descending,
        )

        results = []
        for paper in client.results(search):
            results.append(self._paper_to_dict(paper))

        logger.info("[arxiv] Collected %d papers", len(results))
        return results

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        date_str = since.strftime("%Y%m%d%H%M%S")
        query = kwargs.pop("query", None)
        incremental_query = f"submittedDate:[{date_str} TO *]"
        if query:
            incremental_query += f" AND ({query})"
        return self.collect(query=incremental_query, **kwargs)

    @staticmethod
    def _paper_to_dict(paper: arxiv.Result) -> dict:
        return {
            "arxiv_id": paper.entry_id.split("/")[-1],
            "title": paper.title.replace("\n", " ").strip(),
            "abstract": paper.summary.replace("\n", " ").strip(),
            "authors": json.dumps([a.name for a in paper.authors]),
            "categories": json.dumps(list(paper.categories)),
            "primary_category": paper.primary_category,
            "published": paper.published,
            "updated": paper.updated,
            "doi": paper.doi,
            "pdf_url": paper.pdf_url,
            "entry_url": paper.entry_id,
            "comment": paper.comment,
            "fetched_at": datetime.utcnow(),
        }

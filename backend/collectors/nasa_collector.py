from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from dateutil import parser as date_parser

from backend.collectors.base import BaseCollector
from backend.core.config import AppConfig, get_config, get_secrets

logger = logging.getLogger(__name__)


class NasaCollector(BaseCollector[dict]):
    source_name = "nasa"

    def _get_source_config(self, config: AppConfig):
        return config.nasa

    def collect(self, query: str | None = None, max_results: int | None = None, **kwargs) -> list[dict]:
        config = get_config().nasa
        if not config.enabled:
            return []

        query = query or kwargs.get("keyword") or "artificial intelligence engineering"
        max_results = max_results or config.ntrs.max_results_per_query
        items: list[dict] = []

        if config.ntrs.enabled:
            items.extend(self._collect_ntrs(query, max_results))
        if config.techport.enabled:
            items.extend(self._collect_techport(query, max_results))

        logger.info("[nasa] Collected %d NASA items", len(items))
        return items

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        return self.collect(**kwargs)

    def _collect_ntrs(self, query: str, max_results: int) -> list[dict]:
        config = get_config().nasa.ntrs
        params = {
            "q": query,
            "size": min(max_results, config.max_results_per_query),
            "from": 0,
        }
        response = self._fetch_with_retry(config.base_url, params=params)
        payload = response.json()
        raw_items = _extract_records(payload)
        return [_ntrs_record_to_item(record) for record in raw_items[:max_results] if _record_title(record)]

    def _collect_techport(self, query: str, max_results: int) -> list[dict]:
        secrets = get_secrets()
        if not secrets.techport_api_token:
            logger.info("[nasa] Skipping TechPort because TECHPORT_API_TOKEN is not configured")
            return []
        config = get_config().nasa.techport
        params = {"search": query, "size": min(max_results, config.max_results_per_query)}
        response = self._fetch_with_retry(config.base_url, params=params | {"api_key": secrets.techport_api_token})
        raw_items = _extract_records(response.json())
        return [_techport_record_to_item(record) for record in raw_items[:max_results] if _record_title(record)]


class AdsCollector(BaseCollector[dict]):
    source_name = "ads"

    def _get_source_config(self, config: AppConfig):
        return config.ads

    def collect(self, query: str | None = None, max_results: int | None = None, **kwargs) -> list[dict]:
        config = get_config().ads
        secrets = get_secrets()
        if not config.enabled or not secrets.ads_api_token:
            logger.info("[ads] Skipping ADS because it is disabled or ADS_API_TOKEN is not configured")
            return []
        params = {
            "q": query or kwargs.get("keyword") or "neural operator",
            "fl": "bibcode,title,abstract,author,keyword,pubdate,doctype,identifier,doi",
            "rows": min(max_results or config.max_results_per_query, config.max_results_per_query),
            "sort": "date desc",
        }
        response = self._fetch_ads(config.base_url, params=params)
        docs = response.json().get("response", {}).get("docs", [])
        return [_ads_doc_to_item(doc) for doc in docs if _record_title(doc)]

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        query = kwargs.pop("query", None)
        since_query = f"pubdate:[{since:%Y-%m} TO *]"
        return self.collect(query=f"({query}) AND {since_query}" if query else since_query, **kwargs)

    def _fetch_ads(self, url: str, params: dict) -> Any:
        self._rate_limit()
        client = self._get_http_client()
        response = client.get(url, params=params, headers={"Authorization": f"Bearer {get_secrets().ads_api_token}"})
        response.raise_for_status()
        return response


def _extract_records(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "content", "documents", "projects", "records"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(payload.get("data"), list):
        return [item for item in payload["data"] if isinstance(item, dict)]
    if isinstance(payload.get("hits"), dict):
        hits = payload["hits"].get("hits")
        if isinstance(hits, list):
            return [hit.get("_source", hit) for hit in hits if isinstance(hit, dict)]
    return []


def _record_title(record: dict) -> str:
    title = record.get("title") or record.get("titleText") or record.get("projectTitle")
    if isinstance(title, list):
        return str(title[0]) if title else ""
    return str(title or "").strip()


def _text(record: dict, *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, list):
            value = "; ".join(str(item) for item in value)
        if value:
            return str(value)
    return None


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(str(value), fuzzy=True)
        return parsed.replace(tzinfo=None)
    except Exception:
        return None


def _json_value(value: Any) -> str | None:
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value


def _ntrs_record_to_item(record: dict) -> dict:
    source_id = str(record.get("id") or record.get("stiId") or record.get("accessionNumber") or _record_title(record))
    links = record.get("links") or record.get("_links") or {}
    pdf_url = _text(record, "pdfUrl", "downloadUrl")
    if not pdf_url and isinstance(links, dict):
        for value in links.values():
            if isinstance(value, dict) and "pdf" in str(value.get("href", "")).lower():
                pdf_url = value.get("href")
                break
    return {
        "source": "ntrs",
        "source_id": source_id,
        "title": _record_title(record),
        "summary": _text(record, "abstract", "description", "summary"),
        "authors": _json_value(record.get("authors") or record.get("creators")),
        "keywords": _json_value(record.get("keywords") or record.get("subjectCategories")),
        "item_type": _text(record, "documentType", "type", "stiType"),
        "published_at": _date(record.get("publicationDate") or record.get("date") or record.get("created")),
        "url": _text(record, "url", "landingPage") or f"https://ntrs.nasa.gov/citations/{source_id}",
        "pdf_url": pdf_url,
        "fetched_at": datetime.utcnow(),
    }


def _techport_record_to_item(record: dict) -> dict:
    source_id = str(record.get("projectId") or record.get("id") or _record_title(record))
    return {
        "source": "techport",
        "source_id": source_id,
        "title": _record_title(record),
        "summary": _text(record, "description", "benefits", "summary"),
        "authors": _json_value(record.get("principalInvestigators") or record.get("organizations")),
        "keywords": _json_value(record.get("technologyAreas") or record.get("keywords")),
        "item_type": "project",
        "published_at": _date(record.get("lastUpdated") or record.get("startDate")) or datetime.utcnow() - timedelta(days=365),
        "url": _text(record, "url") or f"https://techport.nasa.gov/view/{source_id}",
        "pdf_url": None,
        "fetched_at": datetime.utcnow(),
    }


def _ads_doc_to_item(doc: dict) -> dict:
    source_id = str(doc.get("bibcode") or _record_title(doc))
    doi = doc.get("doi")
    doi_value = doi[0] if isinstance(doi, list) and doi else doi
    return {
        "source": "ads",
        "source_id": source_id,
        "title": _record_title(doc),
        "summary": _text(doc, "abstract"),
        "authors": _json_value(doc.get("author")),
        "keywords": _json_value(doc.get("keyword")),
        "item_type": _text(doc, "doctype"),
        "published_at": _date(doc.get("pubdate")),
        "url": f"https://ui.adsabs.harvard.edu/abs/{source_id}/abstract",
        "pdf_url": f"https://doi.org/{doi_value}" if doi_value else None,
        "fetched_at": datetime.utcnow(),
    }

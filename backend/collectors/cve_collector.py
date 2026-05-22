from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser

from backend.collectors.base import BaseCollector
from backend.collectors.html_utils import content_hash
from backend.core.config import AppConfig, get_config

logger = logging.getLogger(__name__)

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV_JSON = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


class CVECollector(BaseCollector[dict]):
    source_name = "cve"

    def _get_source_config(self, config: AppConfig):
        return config.cve

    def collect(self, **kwargs) -> list[dict]:
        config = get_config().cve
        if not config.enabled:
            return []

        results: list[dict] = []
        sources = kwargs.get("sources") or config.sources
        if "nvd" in sources:
            results.extend(self._collect_nvd())
        if "cisa_kev" in sources:
            results.extend(self._collect_cisa_kev())

        min_rank = SEVERITY_RANK.get(config.severity_min, 1)
        filtered = [
            item for item in results
            if SEVERITY_RANK.get((item.get("severity") or "LOW").upper(), 0) >= min_rank
            or item["source"] == "cisa_kev"
        ]
        deduped: dict[str, dict] = {}
        for item in filtered:
            deduped[item["cve_id"]] = item
        return list(deduped.values())

    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        items = self.collect(**kwargs)
        return [
            item for item in items
            if item["published_at"] is None or item["published_at"] >= since
        ]

    def _collect_nvd(self) -> list[dict]:
        config = get_config().cve
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=config.days_back)
        params = {
            "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "resultsPerPage": config.max_results_per_query,
        }
        response = self._fetch_with_retry(NVD_API, params=params)
        data = response.json()
        return [self._nvd_item_to_dict(entry) for entry in data.get("vulnerabilities", [])]

    def _collect_cisa_kev(self) -> list[dict]:
        response = self._fetch_with_retry(CISA_KEV_JSON)
        data = response.json()
        return [self._cisa_item_to_dict(entry) for entry in data.get("vulnerabilities", [])]

    @staticmethod
    def _nvd_item_to_dict(entry: dict) -> dict:
        cve = entry.get("cve", {})
        cve_id = cve.get("id", "")
        descriptions = cve.get("descriptions", [])
        description = next((d.get("value") for d in descriptions if d.get("lang") == "en"), None)
        metrics = cve.get("metrics", {})
        severity, score = CVECollector._extract_cvss(metrics)
        refs = [r.get("url") for r in cve.get("references", {}).get("referenceData", []) if r.get("url")]
        affected = cve.get("configurations", [])
        now = datetime.now(timezone.utc)
        published = CVECollector._parse_dt(cve.get("published"))
        modified = CVECollector._parse_dt(cve.get("lastModified"))
        digest = content_hash(cve_id, description, severity, json.dumps(affected, sort_keys=True))
        return {
            "cve_id": cve_id,
            "source": "nvd",
            "title": cve_id,
            "description": description,
            "severity": severity,
            "cvss_score": score,
            "published_at": published,
            "modified_at": modified,
            "references_json": json.dumps(refs, ensure_ascii=False),
            "affected_json": json.dumps(affected, ensure_ascii=False),
            "content_hash": digest,
            "first_seen_at": now,
            "last_seen_at": now,
        }

    @staticmethod
    def _cisa_item_to_dict(entry: dict) -> dict:
        cve_id = entry.get("cveID", "")
        description = entry.get("shortDescription")
        title = entry.get("vulnerabilityName") or cve_id
        affected = {
            "vendorProject": entry.get("vendorProject"),
            "product": entry.get("product"),
            "knownRansomwareCampaignUse": entry.get("knownRansomwareCampaignUse"),
        }
        now = datetime.now(timezone.utc)
        published = CVECollector._parse_dt(entry.get("dateAdded"))
        digest = content_hash(cve_id, title, description, json.dumps(affected, sort_keys=True))
        return {
            "cve_id": cve_id,
            "source": "cisa_kev",
            "title": title,
            "description": description,
            "severity": "HIGH",
            "cvss_score": None,
            "published_at": published,
            "modified_at": published,
            "references_json": json.dumps([entry.get("notes")], ensure_ascii=False),
            "affected_json": json.dumps(affected, ensure_ascii=False),
            "content_hash": digest,
            "first_seen_at": now,
            "last_seen_at": now,
        }

    @staticmethod
    def _extract_cvss(metrics: dict) -> tuple[str | None, float | None]:
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            values = metrics.get(key)
            if values:
                metric = values[0]
                cvss = metric.get("cvssData", {})
                severity = metric.get("baseSeverity") or cvss.get("baseSeverity")
                score = cvss.get("baseScore")
                return severity, score
        return None, None

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        parsed = date_parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

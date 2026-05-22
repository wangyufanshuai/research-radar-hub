from __future__ import annotations

import hashlib
import json
import logging
import urllib.parse
import urllib.robotparser
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generic, TypeVar

import httpx

from backend.core.config import get_config, get_project_root

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseCollector(ABC, Generic[T]):
    source_name: str
    _last_request_time: float = 0.0
    _http_client: httpx.Client | None = None

    def __init__(self) -> None:
        config = get_config()
        source_config = self._get_source_config(config)
        self.rate_delay = source_config.rate_limit.request_delay_seconds
        self.retry_config = source_config.retry
        self.cache_config = config.cache
        self.compliance_config = config.compliance
        self.robots_required = getattr(source_config, "robots_required", True)
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    @abstractmethod
    def _get_source_config(self, config):
        ...

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                headers={"User-Agent": self.compliance_config.user_agent},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._http_client

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_delay:
            time.sleep(self.rate_delay - elapsed)
        self._last_request_time = time.time()

    def _fetch_with_retry(self, url: str, params: dict | None = None) -> httpx.Response:
        self._rate_limit()
        if not self._robots_allowed(url):
            raise PermissionError(f"robots.txt disallows fetch for {url}")

        if self.cache_config.enabled:
            cached = self._read_cache(url, params)
            if cached is not None:
                logger.debug("[%s] Cache hit: %s", self.source_name, url)
                return cached

        last_exception = None
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                client = self._get_http_client()
                response = client.get(url, params=params)

                if response.status_code in self.retry_config.retryable_status_codes:
                    raise httpx.HTTPStatusError(
                        f"Status {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                if len(response.content) > self.compliance_config.max_body_bytes:
                    raise ValueError(
                        f"Response body exceeds configured max_body_bytes for {url}"
                    )

                if self.cache_config.enabled:
                    self._write_cache(url, params, response)

                return response

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                status_code = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
                if status_code in {401, 403, 429}:
                    logger.error(
                        "[%s] Stopping collection for %s after status %s",
                        self.source_name,
                        url,
                        status_code,
                    )
                    raise
                last_exception = e
                if attempt < self.retry_config.max_retries:
                    backoff = min(
                        self.retry_config.backoff_factor ** attempt,
                        self.retry_config.backoff_max_seconds,
                    )
                    logger.warning(
                        "[%s] Attempt %d failed for %s: %s. Retrying in %.1fs",
                        self.source_name,
                        attempt + 1,
                        url,
                        e,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "[%s] All %d attempts failed for %s",
                        self.source_name,
                        self.retry_config.max_retries + 1,
                        url,
                    )

        raise last_exception  # type: ignore

    def _robots_allowed(self, url: str) -> bool:
        if not self.compliance_config.respect_robots_txt or not self.robots_required:
            return True

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return True

        origin = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots_cache.get(origin)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(urllib.parse.urljoin(origin, "/robots.txt"))
            try:
                parser.read()
            except Exception as exc:
                logger.warning("[%s] Could not read robots.txt for %s: %s", self.source_name, origin, exc)
                return False
            self._robots_cache[origin] = parser

        return parser.can_fetch(self.compliance_config.user_agent, url)

    def _cache_key(self, url: str, params: dict | None) -> str:
        raw = url + json.dumps(params or {}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return get_project_root() / self.cache_config.directory / f"{key}.json"

    def _write_cache(self, url: str, params: dict | None, response: httpx.Response) -> None:
        path = self._cache_path(self._cache_key(url, params))
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "url": str(response.url),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _read_cache(self, url: str, params: dict | None) -> httpx.Response | None:
        path = self._cache_path(self._cache_key(url, params))
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["cached_at"])
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age > self.cache_config.default_ttl_seconds:
            return None

        headers = {
            key: value
            for key, value in data["headers"].items()
            if key.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
        }
        return httpx.Response(
            status_code=data["status_code"],
            headers=headers,
            text=data["body"],
            request=httpx.Request("GET", data["url"]),
        )

    @abstractmethod
    def collect(self, **kwargs) -> list[dict]:
        ...

    @abstractmethod
    def collect_incremental(self, since: datetime, **kwargs) -> list[dict]:
        ...

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

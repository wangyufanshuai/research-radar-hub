from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import httpx

from backend.collectors.cve_collector import CVECollector
from backend.collectors.html_utils import content_hash, extract_selected_text
from backend.collectors.school_notice_collector import SchoolNoticeCollector
from backend.collectors.website_change_collector import WebsiteChangeCollector
from backend.core.config import SchoolNoticeSource, WebsitePageConfig


def test_html_extract_selected_text_and_hash() -> None:
    title, text = extract_selected_text(
        "<html><head><title>T</title></head><body><main>Hello   world</main></body></html>",
        "main",
    )
    assert title == "T"
    assert text == "Hello world"
    assert content_hash(text) == content_hash("Hello world")


def test_school_notice_extracts_links_without_private_data(monkeypatch) -> None:
    collector = SchoolNoticeCollector()
    html = """
    <html><body>
      <a href="/n/1">研究生招生考试通知 2026-05-19</a>
      <a href="/n/2">食堂菜单</a>
    </body></html>
    """
    monkeypatch.setattr(
        collector,
        "_fetch_with_retry",
        lambda url: httpx.Response(200, text=html, request=httpx.Request("GET", url)),
    )
    source = SchoolNoticeSource(
        id="fixture",
        name="Fixture School",
        url="https://example.edu/notices/",
        selector="a",
        keywords=["研究生", "考试"],
    )

    items = collector._collect_source(source)

    assert len(items) == 1
    assert items[0]["title"].startswith("研究生招生考试通知")
    assert items[0]["url"] == "https://example.edu/n/1"
    assert "content_hash" in items[0]


def test_website_change_skips_unchanged_content(monkeypatch) -> None:
    collector = WebsiteChangeCollector()
    html = "<html><head><title>Page</title></head><body><main>same content</main></body></html>"
    monkeypatch.setattr(
        collector,
        "_fetch_with_retry",
        lambda url: httpx.Response(200, text=html, request=httpx.Request("GET", url)),
    )
    page = WebsitePageConfig(name="Fixture", url="https://example.edu/", selector="main")
    previous = content_hash("same content")

    assert collector._collect_page(page, previous, "same content") is None


def test_website_change_returns_snapshot_for_changed_content(monkeypatch) -> None:
    collector = WebsiteChangeCollector()
    html = "<html><head><title>Page</title></head><body><main>new content</main></body></html>"
    monkeypatch.setattr(
        collector,
        "_fetch_with_retry",
        lambda url: httpx.Response(200, text=html, request=httpx.Request("GET", url)),
    )
    page = WebsitePageConfig(name="Fixture", url="https://example.edu/", selector="main")

    item = collector._collect_page(page, content_hash("old content"), "old content")

    assert item is not None
    assert item["page"]["last_hash"] == content_hash("new content")
    assert item["snapshot"]["title"] == "Page"
    assert "old content" in item["snapshot"]["diff_summary"]


def test_cve_nvd_mapping_uses_public_metadata_only() -> None:
    entry = {
        "cve": {
            "id": "CVE-2026-0001",
            "published": "2026-05-19T00:00:00.000",
            "lastModified": "2026-05-19T01:00:00.000",
            "descriptions": [{"lang": "en", "value": "A test vulnerability."}],
            "metrics": {
                "cvssMetricV31": [
                    {"cvssData": {"baseScore": 7.5}, "baseSeverity": "HIGH"}
                ]
            },
            "references": {"referenceData": [{"url": "https://example.com/cve"}]},
            "configurations": [{"nodes": []}],
        }
    }

    item = CVECollector._nvd_item_to_dict(entry)

    assert item["cve_id"] == "CVE-2026-0001"
    assert item["source"] == "nvd"
    assert item["severity"] == "HIGH"
    assert item["cvss_score"] == 7.5

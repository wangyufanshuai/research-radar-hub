from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.collectors.arxiv_collector import ArxivCollector
from backend.collectors.cve_collector import CVECollector
from backend.collectors.course_collector import CourseCollector
from backend.collectors.github_collector import GitHubCollector
from backend.collectors.hn_collector import HNCollector
from backend.collectors.school_notice_collector import SchoolNoticeCollector
from backend.collectors.website_change_collector import WebsiteChangeCollector
from backend.models.fetch_log import FetchLog
from backend.models.page_snapshot import PageSnapshot
from backend.repositories.cve_repo import CVERepository
from backend.repositories.course_item_repo import CourseItemRepository
from backend.repositories.fetch_log_repo import FetchLogRepository
from backend.repositories.notice_repo import NoticeRepository
from backend.repositories.paper_repo import PaperRepository
from backend.repositories.repo_repo import RepoRepository
from backend.repositories.story_repo import StoryRepository
from backend.repositories.watched_page_repo import PageSnapshotRepository, WatchedPageRepository
from backend.core.config import WebsitePageConfig

COLLECTORS: dict[str, tuple[type, type | None, str | None]] = {
    "arxiv": (ArxivCollector, PaperRepository, "arxiv_id"),
    "github": (GitHubCollector, RepoRepository, "github_id"),
    "hn": (HNCollector, StoryRepository, "hn_id"),
    "school": (SchoolNoticeCollector, NoticeRepository, "url"),
    "cve": (CVECollector, CVERepository, "cve_id"),
    "course": (CourseCollector, CourseItemRepository, "url"),
    "website": (WebsiteChangeCollector, None, None),
}


def collect_source(db: Session, source: str, incremental: bool = False) -> dict[str, Any]:
    if source not in COLLECTORS:
        allowed = ", ".join([*COLLECTORS.keys(), "all"])
        raise ValueError(f"Unknown source: {source}. Use: {allowed}")

    started_at = datetime.utcnow()
    start_time = time.time()
    collector = None

    try:
        entry = COLLECTORS[source]
        if isinstance(entry, tuple):
            collector_class, repo_class, upsert_field = entry
        else:
            collector_class, repo_class, upsert_field = _legacy_entry(source, entry)
        collector = collector_class()
        fetch_log_repo = FetchLogRepository(db)

        kwargs: dict[str, Any] = {}
        if source == "website":
            kwargs.update(_website_previous_state(db))
            db_pages = _website_pages_from_db(db)
            if db_pages:
                kwargs["pages"] = db_pages

        if incremental:
            last = fetch_log_repo.get_last_success(source)
            items = collector.collect_incremental(since=last.started_at, **kwargs) if last else collector.collect(**kwargs)
        else:
            items = collector.collect(**kwargs)

        if source == "website":
            new_count, updated_count = _save_website_items(db, items)
        else:
            repo = repo_class(db)  # type: ignore[misc]
            new_count, updated_count = repo.bulk_upsert(upsert_field, items)  # type: ignore[arg-type]

        duration = time.time() - start_time
        db.add(
            FetchLog(
                source=source,
                status="success",
                records_fetched=len(items),
                records_new=new_count,
                records_updated=updated_count,
                started_at=started_at,
                finished_at=datetime.utcnow(),
                duration_secs=duration,
            )
        )
        db.commit()
        return {
            "source": source,
            "status": "success",
            "records_fetched": len(items),
            "records_new": new_count,
            "records_updated": updated_count,
            "duration_secs": round(duration, 2),
            "error": None,
        }
    except Exception as exc:
        db.rollback()
        duration = time.time() - start_time
        db.add(
            FetchLog(
                source=source,
                status="failed",
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.utcnow(),
                duration_secs=duration,
            )
        )
        db.commit()
        raise
    finally:
        if collector is not None:
            collector.close()


def _website_previous_state(db: Session) -> dict[str, dict[str, str | None]]:
    page_repo = WatchedPageRepository(db)
    snapshot_repo = PageSnapshotRepository(db)
    hashes: dict[str, str | None] = {}
    texts: dict[str, str | None] = {}
    for page in page_repo.list_all(limit=1000):
        hashes[page.url] = page.last_hash
        latest = (
            snapshot_repo.session.query(PageSnapshot)
            .filter(PageSnapshot.watched_page_id == page.id)
            .order_by(PageSnapshot.fetched_at.desc())
            .first()
        )
        texts[page.url] = latest.text_excerpt if latest else None
    return {"previous_hashes": hashes, "previous_texts": texts}


def _website_pages_from_db(db: Session) -> list[WebsitePageConfig]:
    page_repo = WatchedPageRepository(db)
    return [
        WebsitePageConfig(
            name=page.name,
            url=page.url,
            selector=page.selector,
            render=page.render,
            enabled=page.enabled,
            check_interval_minutes=page.check_interval_minutes,
        )
        for page in page_repo.list_enabled()
    ]


def _legacy_entry(source: str, collector_class: type) -> tuple[type, type | None, str | None]:
    repo_map = {
        "arxiv": (PaperRepository, "arxiv_id"),
        "github": (RepoRepository, "github_id"),
        "hn": (StoryRepository, "hn_id"),
        "school": (NoticeRepository, "url"),
        "cve": (CVERepository, "cve_id"),
        "course": (CourseItemRepository, "url"),
        "website": (None, None),
    }
    repo_class, upsert_field = repo_map[source]
    return collector_class, repo_class, upsert_field


def _save_website_items(db: Session, items: list[dict]) -> tuple[int, int]:
    page_repo = WatchedPageRepository(db)
    new_count = 0
    updated_count = 0
    for item in items:
        page_data = item["page"]
        existing = page_repo.get_by_field("url", page_data["url"])
        page = page_repo.upsert_by_field("url", page_data["url"], page_data)
        if existing is None:
            new_count += 1
        else:
            updated_count += 1

        snapshot_data = item["snapshot"] | {"watched_page_id": page.id}
        db.add(PageSnapshot(**snapshot_data))
    db.flush()
    return new_count, updated_count

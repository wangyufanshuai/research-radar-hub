from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import (
    CVEListResponse,
    CourseItemListResponse,
    NoticeListResponse,
    PageSnapshotListResponse,
)
from backend.models.page_snapshot import PageSnapshot
from backend.repositories.cve_repo import CVERepository
from backend.repositories.course_item_repo import CourseItemRepository
from backend.repositories.notice_repo import NoticeRepository
from backend.repositories.watched_page_repo import PageSnapshotRepository

router = APIRouter(prefix="/api/v1/radar", tags=["radar"])


@router.get("/notices", response_model=NoticeListResponse)
async def list_notices(
    keyword: str | None = None,
    source_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> NoticeListResponse:
    repo = NoticeRepository(db)
    return NoticeListResponse(
        items=repo.search(keyword, source_id, date_from, date_to, offset, limit),
        total=repo.search_count(keyword, source_id, date_from, date_to),
        offset=offset,
        limit=limit,
    )


@router.get("/changes", response_model=PageSnapshotListResponse)
async def list_changes(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PageSnapshotListResponse:
    repo = PageSnapshotRepository(db)
    total = repo.count()
    items = repo.latest_changes(offset=offset, limit=limit)
    return PageSnapshotListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/cves", response_model=CVEListResponse)
async def list_cves(
    keyword: str | None = None,
    severity: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CVEListResponse:
    repo = CVERepository(db)
    return CVEListResponse(
        items=repo.search(keyword, severity, date_from, date_to, offset, limit),
        total=repo.search_count(keyword, severity, date_from, date_to),
        offset=offset,
        limit=limit,
    )


@router.get("/courses", response_model=CourseItemListResponse)
async def list_courses(
    keyword: str | None = None,
    institution: str | None = None,
    source_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CourseItemListResponse:
    repo = CourseItemRepository(db)
    return CourseItemListResponse(
        items=repo.search(keyword, institution, source_id, date_from, date_to, offset, limit),
        total=repo.search_count(keyword, institution, source_id, date_from, date_to),
        offset=offset,
        limit=limit,
    )

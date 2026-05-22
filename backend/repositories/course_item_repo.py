from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.course_item import CourseItem
from backend.repositories.base import BaseRepository


class CourseItemRepository(BaseRepository[CourseItem]):
    def __init__(self, session: Session):
        super().__init__(CourseItem, session)

    def search(
        self,
        keyword: str | None = None,
        institution: str | None = None,
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[CourseItem]:
        stmt = select(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.summary.ilike(f"%{keyword}%")
                | self.model.department.ilike(f"%{keyword}%")
                | self.model.topics.ilike(f"%{keyword}%")
            )
        if institution:
            stmt = stmt.where(self.model.institution == institution)
        if source_id:
            stmt = stmt.where(self.model.source_id == source_id)
        if date_from:
            stmt = stmt.where(self.model.last_seen_at >= date_from)
        if date_to:
            stmt = stmt.where(self.model.last_seen_at <= date_to)
        stmt = stmt.order_by(self.model.last_seen_at.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search_count(
        self,
        keyword: str | None = None,
        institution: str | None = None,
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.summary.ilike(f"%{keyword}%")
                | self.model.department.ilike(f"%{keyword}%")
                | self.model.topics.ilike(f"%{keyword}%")
            )
        if institution:
            stmt = stmt.where(self.model.institution == institution)
        if source_id:
            stmt = stmt.where(self.model.source_id == source_id)
        if date_from:
            stmt = stmt.where(self.model.last_seen_at >= date_from)
        if date_to:
            stmt = stmt.where(self.model.last_seen_at <= date_to)
        return self.session.execute(stmt).scalar_one()

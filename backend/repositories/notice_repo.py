from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.notice import Notice
from backend.repositories.base import BaseRepository


class NoticeRepository(BaseRepository[Notice]):
    def __init__(self, session: Session):
        super().__init__(Notice, session)

    def search(
        self,
        keyword: str | None = None,
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Notice]:
        stmt = select(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.summary.ilike(f"%{keyword}%")
            )
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
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.summary.ilike(f"%{keyword}%")
            )
        if source_id:
            stmt = stmt.where(self.model.source_id == source_id)
        if date_from:
            stmt = stmt.where(self.model.last_seen_at >= date_from)
        if date_to:
            stmt = stmt.where(self.model.last_seen_at <= date_to)
        return self.session.execute(stmt).scalar_one()

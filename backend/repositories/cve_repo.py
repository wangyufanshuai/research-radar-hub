from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.cve_item import CVEItem
from backend.repositories.base import BaseRepository


class CVERepository(BaseRepository[CVEItem]):
    def __init__(self, session: Session):
        super().__init__(CVEItem, session)

    def search(
        self,
        keyword: str | None = None,
        severity: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[CVEItem]:
        stmt = select(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.cve_id.ilike(f"%{keyword}%")
                | self.model.title.ilike(f"%{keyword}%")
                | self.model.description.ilike(f"%{keyword}%")
            )
        if severity:
            stmt = stmt.where(self.model.severity == severity.upper())
        if date_from:
            stmt = stmt.where(self.model.published_at >= date_from)
        if date_to:
            stmt = stmt.where(self.model.published_at <= date_to)
        stmt = stmt.order_by(self.model.published_at.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search_count(
        self,
        keyword: str | None = None,
        severity: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.cve_id.ilike(f"%{keyword}%")
                | self.model.title.ilike(f"%{keyword}%")
                | self.model.description.ilike(f"%{keyword}%")
            )
        if severity:
            stmt = stmt.where(self.model.severity == severity.upper())
        if date_from:
            stmt = stmt.where(self.model.published_at >= date_from)
        if date_to:
            stmt = stmt.where(self.model.published_at <= date_to)
        return self.session.execute(stmt).scalar_one()

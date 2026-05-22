from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.paper import Paper
from backend.repositories.base import BaseRepository


class PaperRepository(BaseRepository[Paper]):
    def __init__(self, session: Session):
        super().__init__(Paper, session)

    def search(
        self,
        keyword: str | None = None,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Paper]:
        stmt = select(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.abstract.ilike(f"%{keyword}%")
            )
        if category:
            stmt = stmt.where(self.model.primary_category == category)
        if date_from:
            stmt = stmt.where(self.model.published >= date_from)
        if date_to:
            stmt = stmt.where(self.model.published <= date_to)
        stmt = stmt.order_by(self.model.published.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search_count(
        self,
        keyword: str | None = None,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.abstract.ilike(f"%{keyword}%")
            )
        if category:
            stmt = stmt.where(self.model.primary_category == category)
        if date_from:
            stmt = stmt.where(self.model.published >= date_from)
        if date_to:
            stmt = stmt.where(self.model.published <= date_to)
        return self.session.execute(stmt).scalar_one()

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.story import Story
from backend.repositories.base import BaseRepository


class StoryRepository(BaseRepository[Story]):
    def __init__(self, session: Session):
        super().__init__(Story, session)

    def search(
        self,
        keyword: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        item_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Story]:
        stmt = select(self.model)
        if keyword:
            stmt = stmt.where(self.model.title.ilike(f"%{keyword}%"))
        if min_score is not None:
            stmt = stmt.where(self.model.score >= min_score)
        if max_score is not None:
            stmt = stmt.where(self.model.score <= max_score)
        if item_type:
            stmt = stmt.where(self.model.item_type == item_type)
        if date_from:
            stmt = stmt.where(self.model.time_published >= date_from)
        if date_to:
            stmt = stmt.where(self.model.time_published <= date_to)
        stmt = stmt.order_by(self.model.score.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search_count(
        self,
        keyword: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        item_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if keyword:
            stmt = stmt.where(self.model.title.ilike(f"%{keyword}%"))
        if min_score is not None:
            stmt = stmt.where(self.model.score >= min_score)
        if max_score is not None:
            stmt = stmt.where(self.model.score <= max_score)
        if item_type:
            stmt = stmt.where(self.model.item_type == item_type)
        if date_from:
            stmt = stmt.where(self.model.time_published >= date_from)
        if date_to:
            stmt = stmt.where(self.model.time_published <= date_to)
        return self.session.execute(stmt).scalar_one()

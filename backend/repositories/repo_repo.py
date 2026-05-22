from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.repo import Repo
from backend.repositories.base import BaseRepository


class RepoRepository(BaseRepository[Repo]):
    def __init__(self, session: Session):
        super().__init__(Repo, session)

    def search(
        self,
        keyword: str | None = None,
        language: str | None = None,
        min_stars: int | None = None,
        max_stars: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Repo]:
        stmt = select(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.full_name.ilike(f"%{keyword}%")
                | self.model.description.ilike(f"%{keyword}%")
            )
        if language:
            stmt = stmt.where(self.model.language == language)
        if min_stars is not None:
            stmt = stmt.where(self.model.stars >= min_stars)
        if max_stars is not None:
            stmt = stmt.where(self.model.stars <= max_stars)
        if date_from:
            stmt = stmt.where(self.model.pushed_at_gh >= date_from)
        if date_to:
            stmt = stmt.where(self.model.pushed_at_gh <= date_to)
        stmt = stmt.order_by(self.model.stars.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search_count(
        self,
        keyword: str | None = None,
        language: str | None = None,
        min_stars: int | None = None,
        max_stars: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        if keyword:
            stmt = stmt.where(
                self.model.full_name.ilike(f"%{keyword}%")
                | self.model.description.ilike(f"%{keyword}%")
            )
        if language:
            stmt = stmt.where(self.model.language == language)
        if min_stars is not None:
            stmt = stmt.where(self.model.stars >= min_stars)
        if max_stars is not None:
            stmt = stmt.where(self.model.stars <= max_stars)
        if date_from:
            stmt = stmt.where(self.model.pushed_at_gh >= date_from)
        if date_to:
            stmt = stmt.where(self.model.pushed_at_gh <= date_to)
        return self.session.execute(stmt).scalar_one()

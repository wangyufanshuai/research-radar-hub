from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.nasa_item import NasaItem
from backend.repositories.base import BaseRepository


class NasaItemRepository(BaseRepository[NasaItem]):
    def __init__(self, session: Session):
        super().__init__(NasaItem, session)

    def get_by_source_identity(self, source: str, source_id: str) -> NasaItem | None:
        stmt = select(self.model).where(self.model.source == source, self.model.source_id == source_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_items(self, items: list[dict]) -> tuple[int, int]:
        new_count = 0
        updated_count = 0
        for item in items:
            source = item.get("source")
            source_id = item.get("source_id")
            if not source or not source_id:
                continue
            existing = self.get_by_source_identity(str(source), str(source_id))
            if existing is None:
                self.session.add(self.model(**item))
                new_count += 1
            else:
                for key, value in item.items():
                    if key not in {"id", "created_at", "first_seen_at"}:
                        setattr(existing, key, value)
                updated_count += 1
        self.session.flush()
        return new_count, updated_count

    def search(self, keyword: str | None = None, offset: int = 0, limit: int = 50) -> list[NasaItem]:
        stmt = select(self.model)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                self.model.title.ilike(pattern)
                | self.model.summary.ilike(pattern)
                | self.model.keywords.ilike(pattern)
            )
        stmt = stmt.order_by(self.model.published_at.desc().nullslast(), self.model.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def recent(self, since: datetime | None = None, limit: int = 100) -> list[NasaItem]:
        stmt = select(self.model)
        if since:
            stmt = stmt.where((self.model.published_at == None) | (self.model.published_at >= since))  # noqa: E711
        stmt = stmt.order_by(self.model.published_at.desc().nullslast(), self.model.created_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

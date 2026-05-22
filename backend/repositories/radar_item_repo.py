from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.radar_item import RadarItem
from backend.repositories.base import BaseRepository


class RadarItemRepository(BaseRepository[RadarItem]):
    def __init__(self, session: Session):
        super().__init__(RadarItem, session)

    def upsert_item(self, data: dict) -> RadarItem:
        stmt = select(self.model).where(
            self.model.source == data["source"],
            self.model.source_id == data["source_id"],
            self.model.topic_key == data["topic_key"],
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing is None:
            item = self.model(**data)
            self.session.add(item)
            self.session.flush()
            return item
        for key, value in data.items():
            if key not in {"id", "created_at"}:
                setattr(existing, key, value)
        self.session.flush()
        return existing

    def list_for_report(
        self,
        date_from: datetime,
        date_to: datetime,
        topic_key: str | None = None,
        limit: int = 100,
    ) -> list[RadarItem]:
        stmt = select(self.model).where(
            self.model.include_in_report.is_(True),
            self.model.published_at >= date_from,
            self.model.published_at <= date_to,
        )
        if topic_key:
            stmt = stmt.where(self.model.topic_key == topic_key)
        stmt = stmt.order_by(self.model.topic_key.asc(), self.model.score.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

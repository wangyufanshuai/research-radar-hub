from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.base import TimestampMixin

ModelType = TypeVar("ModelType", bound=TimestampMixin)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, id: int) -> ModelType | None:
        return self.session.get(self.model, id)

    def get_by_field(self, field: str, value: Any) -> ModelType | None:
        stmt = select(self.model).where(getattr(self.model, field) == value)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        filters: dict[str, Any] | None = None,
        order_by: Any = None,
    ) -> Sequence[ModelType]:
        stmt = select(self.model)
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def count(self, filters: dict[str, Any] | None = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        if filters:
            for field, value in filters.items():
                stmt = stmt.where(getattr(self.model, field) == value)
        return self.session.execute(stmt).scalar_one()

    def upsert_by_field(self, field: str, value: Any, data: dict) -> ModelType:
        existing = self.get_by_field(field, value)
        if existing is None:
            instance = self.model(**data)
            self.session.add(instance)
            self.session.flush()
            return instance
        else:
            for key, val in data.items():
                if key not in ("id", "created_at", "first_seen_at"):
                    setattr(existing, key, val)
            self.session.flush()
            return existing

    def bulk_upsert(self, field: str, items: list[dict]) -> tuple[int, int]:
        new_count = 0
        updated_count = 0
        for item in items:
            value = item.get(field)
            if value is None:
                continue
            existing = self.get_by_field(field, value)
            if existing is None:
                self.session.add(self.model(**item))
                new_count += 1
            else:
                for key, val in item.items():
                    if key not in ("id", "created_at", "first_seen_at"):
                        setattr(existing, key, val)
                updated_count += 1
        self.session.flush()
        return new_count, updated_count

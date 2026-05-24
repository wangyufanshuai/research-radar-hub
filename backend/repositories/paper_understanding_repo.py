from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.paper_understanding import PaperUnderstanding
from backend.repositories.base import BaseRepository


class PaperUnderstandingRepository(BaseRepository[PaperUnderstanding]):
    def __init__(self, session: Session):
        super().__init__(PaperUnderstanding, session)

    def get_by_source_identity(self, source: str, source_id: str) -> PaperUnderstanding | None:
        stmt = select(self.model).where(self.model.source == source, self.model.source_id == source_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_understanding(self, data: dict) -> PaperUnderstanding:
        source = str(data["source"])
        source_id = str(data["source_id"])
        existing = self.get_by_source_identity(source, source_id)
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

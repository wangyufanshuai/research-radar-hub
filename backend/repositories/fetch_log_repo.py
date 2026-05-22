from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.fetch_log import FetchLog
from backend.repositories.base import BaseRepository


class FetchLogRepository(BaseRepository[FetchLog]):
    def __init__(self, session: Session):
        super().__init__(FetchLog, session)

    def get_last_success(self, source: str) -> FetchLog | None:
        stmt = (
            select(self.model)
            .where(self.model.source == source, self.model.status == "success")
            .order_by(self.model.started_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

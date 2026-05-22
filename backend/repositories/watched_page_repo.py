from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.page_snapshot import PageSnapshot
from backend.models.watched_page import WatchedPage
from backend.repositories.base import BaseRepository


class WatchedPageRepository(BaseRepository[WatchedPage]):
    def __init__(self, session: Session):
        super().__init__(WatchedPage, session)

    def list_enabled(self) -> list[WatchedPage]:
        stmt = select(self.model).where(self.model.enabled.is_(True))
        return list(self.session.execute(stmt).scalars().all())


class PageSnapshotRepository(BaseRepository[PageSnapshot]):
    def __init__(self, session: Session):
        super().__init__(PageSnapshot, session)

    def latest_changes(self, offset: int = 0, limit: int = 20) -> list[PageSnapshot]:
        stmt = (
            select(self.model)
            .order_by(self.model.fetched_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.daily_report import DailyReport
from backend.repositories.base import BaseRepository


class DailyReportRepository(BaseRepository[DailyReport]):
    def __init__(self, session: Session):
        super().__init__(DailyReport, session)

    def get_by_date_kind(self, report_date: date, kind: str) -> DailyReport | None:
        stmt = select(self.model).where(
            self.model.report_date == report_date,
            self.model.kind == kind,
        )
        return self.session.execute(stmt).scalar_one_or_none()

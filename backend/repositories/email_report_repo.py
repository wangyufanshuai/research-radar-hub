from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.email_report import EmailReport
from backend.repositories.base import BaseRepository


class EmailReportRepository(BaseRepository[EmailReport]):
    def __init__(self, session: Session):
        super().__init__(EmailReport, session)

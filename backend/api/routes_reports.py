from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import DailyReportResponse, EmailReportResponse
from backend.repositories.daily_report_repo import DailyReportRepository
from backend.services.email import send_daily_report_email
from backend.services.daily_report import generate_daily_report
from backend.services.research_radar import write_report_html

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/daily", response_model=DailyReportResponse)
async def get_daily_report(
    report_date: date | None = Query(None, alias="date"),
    kind: str = "all",
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> DailyReportResponse:
    target_date = report_date or date.today()
    repo = DailyReportRepository(db)
    report = None if refresh else repo.get_by_date_kind(target_date, kind)
    if report is None:
        report = generate_daily_report(db, target_date, kind)
    return report


@router.post("/daily/send", response_model=EmailReportResponse)
async def send_daily_report(
    report_date: date | None = Query(None, alias="date"),
    kind: str = "research",
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> EmailReportResponse:
    target_date = report_date or date.today()
    repo = DailyReportRepository(db)
    report = None if refresh else repo.get_by_date_kind(target_date, kind)
    if report is None:
        report = generate_daily_report(db, target_date, kind)
    output_path = write_report_html(report.body_markdown, target_date)
    return send_daily_report_email(db, report, output_path=output_path)

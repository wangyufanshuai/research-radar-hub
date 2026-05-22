"""CLI: python -m backend.scripts.research_radar --collect --send"""
from __future__ import annotations

import argparse
import logging
from datetime import date

from backend.core.database import get_session_factory, init_db
from backend.core.logging import setup_logging
from backend.services.collection import collect_source
from backend.services.daily_report import generate_daily_report
from backend.services.email import send_daily_report_email
from backend.services.research_radar import write_report_html


def run(collect: bool = False, send: bool = False, report_date: date | None = None) -> None:
    init_db()
    session = get_session_factory()()
    target_date = report_date or date.today()
    try:
        if collect:
            for source in ("arxiv", "github", "course"):
                try:
                    result = collect_source(session, source, incremental=True)
                    print(
                        "{source}: fetched={records_fetched} new={records_new} "
                        "updated={records_updated}".format(**result)
                    )
                except Exception as exc:
                    session.rollback()
                    logging.error("[%s] Research radar collection failed: %s", source, exc)
                    print(f"{source}: failed - {exc}")

        report = generate_daily_report(session, target_date, kind="research")
        output_path = write_report_html(report.body_markdown, target_date)
        print(f"Wrote report: {output_path}")

        if send:
            email_report = send_daily_report_email(session, report, output_path=output_path)
            print(f"Email status: {email_report.status}")
            if email_report.error_message:
                print(f"Email error: {email_report.error_message}")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and optionally email the research radar report")
    parser.add_argument("--collect", action="store_true", help="Run incremental arXiv, GitHub, and course collection first")
    parser.add_argument("--send", action="store_true", help="Send the generated report through SMTP")
    parser.add_argument("--date", help="Report date in YYYY-MM-DD format; defaults to today")
    args = parser.parse_args()

    setup_logging()
    report_date = date.fromisoformat(args.date) if args.date else None
    run(collect=args.collect, send=args.send, report_date=report_date)


if __name__ == "__main__":
    main()

"""CLI: python -m backend.scripts.daily_report --kind all"""
from __future__ import annotations

import argparse
from datetime import date

from backend.core.database import get_session_factory, init_db
from backend.core.logging import setup_logging
from backend.services.daily_report import generate_daily_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Markdown daily report")
    parser.add_argument("--kind", default="all", choices=["all", "school", "arxiv", "github", "website", "cve"])
    parser.add_argument("--date", dest="report_date", default=None, help="YYYY-MM-DD")
    args = parser.parse_args()

    setup_logging()
    init_db()
    session = get_session_factory()()
    try:
        target_date = date.fromisoformat(args.report_date) if args.report_date else None
        report = generate_daily_report(session, target_date, args.kind)
        print(report.title)
        print()
        print(report.body_markdown)
    finally:
        session.close()


if __name__ == "__main__":
    main()

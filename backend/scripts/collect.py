"""CLI: python -m backend.scripts.collect --source arxiv"""
from __future__ import annotations

import argparse
import logging

from backend.core.database import get_session_factory, init_db
from backend.core.logging import setup_logging
from backend.services.collection import COLLECTORS, collect_source as run_collect_source


def collect_source(source: str, incremental: bool = False) -> None:
    init_db()
    session = get_session_factory()()

    sources = list(COLLECTORS.keys()) if source == "all" else [source]

    for src in sources:
        if src not in COLLECTORS:
            print(f"Unknown source: {src}")
            continue

        print(f"\n--- Collecting from {src} ---")
        try:
            result = run_collect_source(session, src, incremental=incremental)
            print(
                "  Fetched: {records_fetched}, New: {records_new}, "
                "Updated: {records_updated}, Duration: {duration_secs}s".format(**result)
            )
        except Exception as e:
            print(f"  Error: {e}")
            logging.error("[%s] Collection failed: %s", src, e)
            session.rollback()

    session.close()


def main():
    parser = argparse.ArgumentParser(description="Collect data from public sources")
    parser.add_argument(
        "--source",
        choices=[*COLLECTORS.keys(), "all"],
        required=True,
        help="Data source to collect from",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only fetch new items since last successful run",
    )
    args = parser.parse_args()

    setup_logging()
    collect_source(args.source, args.incremental)


if __name__ == "__main__":
    main()

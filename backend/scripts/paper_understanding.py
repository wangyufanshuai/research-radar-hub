from __future__ import annotations

import argparse

from backend.core.database import get_session_factory, init_db
from backend.services.paper_understanding import analyze_recent_papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze recent papers with the safe paper-understanding pipeline")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--allow-pdf", action="store_true", help="Download public PDFs within configured safety limits")
    args = parser.parse_args()

    init_db()
    with get_session_factory()() as session:
        results = analyze_recent_papers(session, limit=args.limit, allow_pdf=args.allow_pdf)
        print(f"Analyzed {len(results)} paper/NASA items")
        for item in results:
            print(f"- {item.source}:{item.source_id} {item.understanding_status} {item.title[:100]}")


if __name__ == "__main__":
    main()

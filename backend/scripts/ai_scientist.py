"""CLI: python -m backend.scripts.ai_scientist --topic "..." --run"""
from __future__ import annotations

import argparse

from backend.core.database import get_session_factory, init_db
from backend.core.logging import setup_logging
from backend.services.ai_scientist import create_scientist_task, run_scientist_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and run an AI Scientist workspace task")
    parser.add_argument("--topic", required=True, help="Research topic to investigate")
    parser.add_argument("--run", action="store_true", help="Run the full staged workflow")
    parser.add_argument("--max-papers", type=int, default=20)
    parser.add_argument("--max-repos", type=int, default=10)
    parser.add_argument("--no-llm", action="store_true", help="Disable optional LLM enhancement")
    args = parser.parse_args()

    setup_logging()
    init_db()
    session = get_session_factory()()
    try:
        task = create_scientist_task(session, args.topic)
        print(f"Created AI Scientist task: {task.id}")
        if args.run:
            task = run_scientist_task(
                session,
                task.id,
                max_papers=args.max_papers,
                max_repos=args.max_repos,
                use_llm=not args.no_llm,
            )
            print(f"Task status: {task.status}")
            for run in sorted(task.runs, key=lambda item: item.started_at):
                print(f"- {run.stage}: {run.status} {run.message or run.error_message or ''}")
            reports = [artifact for artifact in task.artifacts if artifact.kind == "report"]
            if reports:
                reports.sort(key=lambda artifact: artifact.created_at_artifact, reverse=True)
                print(f"Report: {reports[0].html_path}")
    finally:
        session.close()


if __name__ == "__main__":
    main()

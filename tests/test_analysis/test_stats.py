from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.analysis.stats import SourceStats, compute_source_stats
from backend.models.paper import Paper
from backend.models.repo import Repo
from backend.models.story import Story

# Capture the real implementation before any patching.
_real_timestamp_now = pd.Timestamp.now


def _naive_now(*args, **kwargs):
    """Return a tz-naive Timestamp to avoid tz-aware vs tz-naive mismatch.

    The production code calls ``pd.Timestamp.now(tz="UTC")`` which returns
    a tz-aware value.  SQLite stores naive datetimes, so pd.read_sql
    produces tz-naive columns.  Comparing the two raises TypeError.
    Dropping the tz argument sidesteps the issue.
    """
    return _real_timestamp_now()


class TestComputeSourceStats:

    @patch("backend.analysis.stats.pd.Timestamp.now", _naive_now)
    def test_empty_db(self, db_session: Session) -> None:
        stats = compute_source_stats(db_session)

        assert isinstance(stats, SourceStats)
        assert stats.total_papers == 0
        assert stats.total_repos == 0
        assert stats.total_stories == 0
        assert stats.papers_last_7d == 0
        assert stats.repos_last_7d == 0
        assert stats.stories_last_7d == 0
        assert stats.top_paper_categories == []
        assert stats.top_repo_languages == []
        assert stats.avg_story_score == 0.0

    @patch("backend.analysis.stats.pd.Timestamp.now", _naive_now)
    def test_with_data(
        self,
        db_session: Session,
        sample_paper_data: dict,
        sample_repo_data: dict,
        sample_story_data: dict,
    ) -> None:
        now = datetime.now()

        for i, (cat_list, primary) in enumerate(
            [
                (["cs.AI", "cs.CL"], "cs.AI"),
                (["cs.AI"], "cs.AI"),
                (["cs.CV"], "cs.CV"),
            ]
        ):
            data = {
                "arxiv_id": f"2401.00{i:02d}",
                "title": f"Test Paper {i}",
                "abstract": f"Abstract for paper {i}",
                "authors": json.dumps(["Author"]),
                "categories": json.dumps(cat_list),
                "primary_category": primary,
                "published": now - timedelta(days=i),
                "fetched_at": now,
            }
            db_session.add(Paper(**data))

        for i, lang in enumerate(["Python", "TypeScript"]):
            db_session.add(Repo(
                github_id=100 + i,
                full_name=f"org/repo-{i}",
                description=f"Repo {i}",
                language=lang,
                stars=100 * (i + 1),
                forks=10,
                open_issues=0,
                watchers=0,
                topics=json.dumps(["topic"]),
                fetched_at=now,
                updated_at_gh=now - timedelta(days=i),
            ))

        for i in range(2):
            db_session.add(Story(
                hn_id=200 + i,
                item_type="story",
                title=f"Story {i}",
                url=f"https://example.com/{i}",
                score=100 * (i + 1),
                author=f"user{i}",
                descendants=10 * i,
                time_published=now - timedelta(days=i),
                fetched_at=now,
            ))

        db_session.commit()

        stats = compute_source_stats(db_session)

        assert stats.total_papers == 3
        assert stats.total_repos == 2
        assert stats.total_stories == 2
        assert stats.papers_last_7d == 3
        assert stats.repos_last_7d == 2
        assert stats.stories_last_7d == 2

        cat_dict = dict(stats.top_paper_categories)
        assert cat_dict.get("cs.AI") == 2
        assert cat_dict.get("cs.CL") == 1
        assert cat_dict.get("cs.CV") == 1

        lang_dict = dict(stats.top_repo_languages)
        assert "Python" in lang_dict
        assert "TypeScript" in lang_dict
        assert stats.avg_story_score == 150.0

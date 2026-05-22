from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from backend.models.paper import Paper
from backend.models.repo import Repo
from backend.models.story import Story


@dataclass
class SourceStats:
    total_papers: int
    total_repos: int
    total_stories: int
    papers_last_7d: int
    repos_last_7d: int
    stories_last_7d: int
    top_paper_categories: list[list]
    top_repo_languages: list[list]
    avg_story_score: float


def compute_source_stats(session: Session) -> SourceStats:
    papers_df = pd.read_sql(session.query(Paper).statement, session.bind)
    repos_df = pd.read_sql(session.query(Repo).statement, session.bind)
    stories_df = pd.read_sql(session.query(Story).statement, session.bind)

    now = pd.Timestamp.now()
    week_ago = now - pd.Timedelta(days=7)

    total_papers = len(papers_df)
    papers_last_7d = (
        len(papers_df[papers_df["published"] >= week_ago]) if total_papers > 0 else 0
    )

    cat_counts: dict[str, int] = {}
    for cats_str in papers_df["categories"].dropna():
        for cat in json.loads(cats_str):
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    top_categories = sorted(cat_counts.items(), key=lambda x: -x[1])[:10]
    top_categories_list = [[c, n] for c, n in top_categories]

    total_repos = len(repos_df)
    repos_last_7d = (
        len(repos_df[repos_df["updated_at_gh"] >= week_ago])
        if total_repos > 0 and "updated_at_gh" in repos_df.columns
        else 0
    )
    lang_counts = repos_df["language"].value_counts().head(10)
    top_languages = [[lang, int(cnt)] for lang, cnt in lang_counts.items()]

    total_stories = len(stories_df)
    stories_last_7d = (
        len(stories_df[stories_df["time_published"] >= week_ago])
        if total_stories > 0
        else 0
    )
    avg_score = float(stories_df["score"].mean()) if total_stories > 0 else 0.0

    return SourceStats(
        total_papers=total_papers,
        total_repos=total_repos,
        total_stories=total_stories,
        papers_last_7d=papers_last_7d,
        repos_last_7d=repos_last_7d,
        stories_last_7d=stories_last_7d,
        top_paper_categories=top_categories_list,
        top_repo_languages=top_languages,
        avg_story_score=round(avg_score, 1),
    )

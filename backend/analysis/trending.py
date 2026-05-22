from __future__ import annotations

import json
import re
from collections import Counter

import pandas as pd
from sqlalchemy.orm import Session

from backend.models.paper import Paper
from backend.models.repo import Repo
from backend.models.story import Story

STOP_WORDS = frozenset({
    "the", "a", "an", "of", "in", "for", "and", "to", "with", "on", "is", "are",
    "from", "by", "that", "this", "or", "at", "as", "it", "we", "our", "their",
    "its", "not", "but", "be", "has", "have", "had", "was", "were", "will", "can",
    "do", "does", "did", "how", "what", "which", "who", "when", "where", "why",
    "all", "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "only", "than", "too", "very", "just", "about", "also", "into", "over",
    "after", "before", "between", "through", "during", "without", "using", "based",
})


def compute_trending_topics(session: Session, days: int = 7) -> list[dict]:
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)

    papers = pd.read_sql(
        session.query(Paper).filter(Paper.published >= cutoff).statement,
        session.bind,
    )
    repos = pd.read_sql(
        session.query(Repo).filter(Repo.pushed_at_gh >= cutoff).statement,
        session.bind,
    )
    stories = pd.read_sql(
        session.query(Story).filter(Story.time_published >= cutoff).statement,
        session.bind,
    )

    word_counts: Counter = Counter()

    for title in papers["title"].dropna():
        words = re.findall(r"[a-zA-Z]{3,}", title.lower())
        word_counts.update(w for w in words if w not in STOP_WORDS)

    for title in stories["title"].dropna():
        words = re.findall(r"[a-zA-Z]{3,}", title.lower())
        word_counts.update(w for w in words if w not in STOP_WORDS)

    for topics_str in repos["topics"].dropna():
        for topic in json.loads(topics_str):
            word_counts[topic.lower()] += 1

    trending = word_counts.most_common(30)
    return [{"keyword": word, "count": count} for word, count in trending]

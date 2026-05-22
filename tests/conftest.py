from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite session that creates/drops all tables per test.

    Uses StaticPool so that every connection shares the same underlying
    sqlite3 connection.  This is required because libraries like pandas
    may open a separate connection via ``session.bind`` when calling
    ``pd.read_sql``, and ``sqlite:///:memory:`` creates an isolated
    database per connection by default.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import backend.models  # noqa: F401 – ensure all models are registered

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def sample_paper_data() -> dict:
    now = datetime.now(tz=timezone.utc)
    return {
        "arxiv_id": "2401.00001",
        "title": "A Study on Transformer Architectures for NLP",
        "abstract": "We propose a novel transformer architecture.",
        "authors": json.dumps(["Alice Smith", "Bob Jones"]),
        "categories": json.dumps(["cs.AI", "cs.CL"]),
        "primary_category": "cs.AI",
        "published": datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        "updated": datetime(2024, 1, 20, 8, 30, 0, tzinfo=timezone.utc),
        "doi": "10.1234/arxiv.2401.00001",
        "pdf_url": "https://arxiv.org/pdf/2401.00001",
        "entry_url": "https://arxiv.org/abs/2401.00001",
        "comment": None,
        "fetched_at": now,
    }


@pytest.fixture()
def sample_repo_data() -> dict:
    now = datetime.now(tz=timezone.utc)
    return {
        "github_id": 123456,
        "full_name": "example/awesome-project",
        "description": "An awesome open-source project",
        "language": "Python",
        "stars": 1500,
        "forks": 200,
        "open_issues": 42,
        "watchers": 100,
        "topics": json.dumps(["machine-learning", "deep-learning", "nlp"]),
        "license_name": "MIT",
        "homepage": "https://awesome-project.example.com",
        "html_url": "https://github.com/example/awesome-project",
        "is_archived": False,
        "created_at_gh": datetime(2023, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at_gh": datetime(2024, 1, 10, 14, 30, 0, tzinfo=timezone.utc),
        "pushed_at_gh": datetime(2024, 1, 10, 14, 30, 0, tzinfo=timezone.utc),
        "fetched_at": now,
    }


@pytest.fixture()
def sample_story_data() -> dict:
    now = datetime.now(tz=timezone.utc)
    return {
        "hn_id": 42,
        "item_type": "story",
        "title": "Show HN: A new approach to distributed systems",
        "url": "https://example.com/distributed-systems",
        "text": None,
        "score": 350,
        "author": "pg",
        "descendants": 120,
        "time_published": datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
        "fetched_at": now,
    }

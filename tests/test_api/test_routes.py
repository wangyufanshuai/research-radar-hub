from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """TestClient wired to an in-memory SQLite database.

    Uses StaticPool so every SQLAlchemy connection reuses the same
    underlying sqlite3 connection.  This is required because
    ``sqlite:///:memory:`` creates a brand-new database per connection
    by default.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign keys on every connection
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    import backend.models  # noqa: F401 – register all models

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def _override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    from backend.api.deps import get_db
    from backend.main import app

    app.dependency_overrides[get_db] = _override_get_db

    # Patch init_db so the app lifespan does not try to create tables
    # on a production engine.
    with patch("backend.main.init_db"):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


class TestHealthCheck:
    def test_health_check(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"


class TestListPapers:
    def test_list_papers_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/papers")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_papers_with_data(self, client: TestClient) -> None:
        from backend.api.deps import get_db
        from backend.main import app

        db_gen = app.dependency_overrides[get_db]()
        db: Session = next(db_gen)

        from backend.models.paper import Paper

        now = datetime.now(tz=timezone.utc)
        paper = Paper(
            arxiv_id="2401.09999",
            title="Test Paper for API",
            abstract="Abstract for API test.",
            authors=json.dumps(["Test Author"]),
            categories=json.dumps(["cs.AI"]),
            primary_category="cs.AI",
            published=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            fetched_at=now,
        )
        db.add(paper)
        db.commit()

        response = client.get("/api/v1/papers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["arxiv_id"] == "2401.09999"
        assert data["items"][0]["title"] == "Test Paper for API"

        db.close()


class TestCollectArxiv:
    def test_collect_arxiv_mocked(self, client: TestClient) -> None:
        now = datetime.now(tz=timezone.utc)
        mock_items = [
            {
                "arxiv_id": "2401.05555",
                "title": "Mocked Arxiv Paper",
                "abstract": "Abstract from mocked collector.",
                "authors": json.dumps(["Mock Author"]),
                "categories": json.dumps(["cs.AI"]),
                "primary_category": "cs.AI",
                "published": datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc),
                "updated": datetime(2024, 1, 12, 0, 0, 0, tzinfo=timezone.utc),
                "doi": None,
                "pdf_url": "https://arxiv.org/pdf/2401.05555",
                "entry_url": "https://arxiv.org/abs/2401.05555",
                "comment": None,
                "fetched_at": now,
            }
        ]

        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_items
        mock_collector.close = MagicMock()

        # COLLECTORS is a module-level dict that maps source names to
        # collector classes.  Patching the class name alone does not
        # update the dict, so we patch the dict entry directly.
        mock_cls = MagicMock(return_value=mock_collector)
        with patch.dict(
            "backend.api.routes_collect.COLLECTORS",
            {"arxiv": mock_cls},
        ):
            response = client.post("/api/v1/collect/arxiv")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "arxiv"
        assert data["status"] == "success"
        assert data["records_fetched"] == 1
        assert data["records_new"] == 1
        assert data["records_updated"] == 0

    def test_collect_all_reports_partial_errors(self, client: TestClient, monkeypatch) -> None:
        from backend.api import routes_collect

        monkeypatch.setattr(
            routes_collect,
            "COLLECTORS",
            {
                "arxiv": object(),
                "course": object(),
            },
        )

        def fake_collect_source(db, source: str, incremental: bool = False):
            if source == "course":
                raise RuntimeError("course source blocked")
            return {
                "source": source,
                "status": "success",
                "records_fetched": 2,
                "records_new": 1,
                "records_updated": 1,
                "duration_secs": 0.5,
                "error": None,
            }

        monkeypatch.setattr(routes_collect, "collect_source", fake_collect_source)

        response = client.post("/api/v1/collect/all?incremental=true")

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "all"
        assert data["status"] == "failed"
        assert data["records_fetched"] == 2
        assert "course: course source blocked" in data["error"]

    def test_frontend_collect_sources_match_backend_contract(self) -> None:
        from pathlib import Path

        text = Path("frontend/src/lib/types.ts").read_text(encoding="utf-8")
        assert '"arxiv" | "github" | "hn" | "course" | "nasa" | "all"' in text
        assert '"papers" | "repos" | "stories"' not in text


class TestAnalysisStats:
    def test_analysis_stats(self, client: TestClient) -> None:
        response = client.get("/api/v1/analysis/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_papers" in data
        assert "total_repos" in data
        assert "total_stories" in data
        assert "papers_last_7d" in data
        assert "repos_last_7d" in data
        assert "stories_last_7d" in data
        assert "top_paper_categories" in data
        assert "top_repo_languages" in data
        assert "avg_story_score" in data
        # Empty database, so all should be zero
        assert data["total_papers"] == 0
        assert data["total_repos"] == 0
        assert data["total_stories"] == 0

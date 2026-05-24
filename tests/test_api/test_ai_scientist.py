from __future__ import annotations

import json
from datetime import datetime
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models.nasa_item import NasaItem
from backend.models.paper import Paper
from backend.models.repo import Repo
from backend.services.ai_scientist import deduplicate_items, plan_query, score_items


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    import backend.models  # noqa: F401

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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_plan_query_extracts_keywords() -> None:
    plan = plan_query("neural operator for relativistic hydrodynamics")

    assert "neural operator" in plan.keywords
    assert "relativistic hydrodynamics" in plan.keywords
    assert 'all:"neural operator for relativistic hydrodynamics"' in plan.arxiv_query


def test_deduplicate_items_by_normalized_title() -> None:
    items = [
        {"source": "arxiv", "source_id": "1", "title": "Neural Operators for Fluids"},
        {"source": "arxiv", "source_id": "2", "title": "Neural operators for fluids!"},
        {"source": "github", "source_id": "3", "title": "operator-lab"},
    ]

    assert len(deduplicate_items(items)) == 2


def test_score_items_is_stable(client: TestClient) -> None:
    from backend.api.deps import get_db
    from backend.main import app

    session = next(app.dependency_overrides[get_db]())
    try:
        plan = plan_query("neural operator for relativistic hydrodynamics")
        scored = score_items(
            session,
            [
                {
                    "source": "arxiv",
                    "source_id": "2605.1",
                    "title": "Neural operator methods for relativistic hydrodynamics",
                    "summary": "A neural operator baseline for fluid simulation.",
                    "url": "https://arxiv.org/abs/2605.1",
                    "published_at": datetime(2026, 5, 22),
                },
                {
                    "source": "github",
                    "source_id": "99",
                    "title": "example/neural-operator-hydro",
                    "summary": "Code for neural operator hydrodynamics experiments.",
                    "url": "https://github.com/example/neural-operator-hydro",
                    "published_at": datetime(2026, 5, 22),
                    "stars": 200,
                    "language": "Python",
                },
            ],
            plan,
        )

        assert scored[0]["relevance_score"] >= scored[1]["relevance_score"]
        assert any(item["selected"] for item in scored)
    finally:
        session.close()


def test_ai_scientist_api_runs_with_mock_data(client: TestClient, monkeypatch) -> None:
    from backend.api.deps import get_db
    from backend.main import app
    from backend.services import ai_scientist

    session = next(app.dependency_overrides[get_db]())
    try:
        session.add(
            Paper(
                arxiv_id="2605.12345",
                title="Neural operator for relativistic hydrodynamics",
                abstract="We study neural operators for relativistic fluid dynamics and simulation.",
                authors=json.dumps(["A. Scientist"]),
                categories=json.dumps(["cs.LG", "physics.comp-ph"]),
                primary_category="cs.LG",
                published=datetime(2026, 5, 22, 8, 0, 0),
                fetched_at=datetime(2026, 5, 22, 8, 1, 0),
            )
        )
        session.add(
            Repo(
                github_id=4242,
                full_name="example/neural-operator-hydro",
                description="Python baseline code for neural operator hydrodynamics.",
                language="Python",
                stars=120,
                forks=10,
                open_issues=1,
                watchers=120,
                topics=json.dumps(["neural-operator", "hydrodynamics"]),
                html_url="https://github.com/example/neural-operator-hydro",
                pushed_at_gh=datetime(2026, 5, 22, 9, 0, 0),
                fetched_at=datetime(2026, 5, 22, 9, 1, 0),
            )
        )
        session.commit()
    finally:
        session.close()

    monkeypatch.setattr(ai_scientist, "_try_collect_arxiv", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_scientist, "_try_collect_github", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_scientist, "_try_collect_nasa", lambda *args, **kwargs: None)

    create_response = client.post(
        "/api/v1/scientist/tasks",
        json={"topic": "neural operator for relativistic hydrodynamics", "max_papers": 5, "max_repos": 5, "use_llm": False},
    )
    assert create_response.status_code == 200
    task_id = create_response.json()["id"]

    run_response = client.post(f"/api/v1/scientist/tasks/{task_id}/run?max_papers=5&max_repos=5&use_llm=false")
    assert run_response.status_code == 200
    data = run_response.json()
    assert data["status"] == "completed"
    assert {run["stage"] for run in data["runs"]} >= {"Planner", "Scout", "Writer"}
    assert any(item["source"] == "arxiv" for item in data["items"])
    assert any(artifact["kind"] == "experiment_plan" for artifact in data["artifacts"])
    assert any(artifact["kind"] == "report" and "AI Scientist Report" in artifact["body_markdown"] for artifact in data["artifacts"])


def test_ai_scientist_empty_task_generates_report(client: TestClient, monkeypatch) -> None:
    from backend.services import ai_scientist

    monkeypatch.setattr(ai_scientist, "_try_collect_arxiv", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_scientist, "_try_collect_github", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_scientist, "_try_collect_nasa", lambda *args, **kwargs: None)

    created = client.post("/api/v1/scientist/tasks", json={"topic": "rare impossible topic", "use_llm": False})
    task_id = created.json()["id"]
    response = client.post(f"/api/v1/scientist/tasks/{task_id}/run?use_llm=false")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["items"] == []
    assert any("No matching papers" in artifact["body_markdown"] for artifact in data["artifacts"] if artifact["kind"] == "report")


def test_ai_scientist_report_includes_nasa_understanding(client: TestClient, monkeypatch) -> None:
    from backend.api.deps import get_db
    from backend.main import app
    from backend.services import ai_scientist

    monkeypatch.setattr(ai_scientist, "_try_collect_arxiv", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_scientist, "_try_collect_github", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_scientist, "_try_collect_nasa", lambda *args, **kwargs: None)

    override = app.dependency_overrides[get_db]
    session_generator = override()
    session = next(session_generator)
    try:
        session.add(
            NasaItem(
                source="ntrs",
                source_id="nasa-1",
                title="Neural Operator Benchmark for Relativistic Hydrodynamics",
                summary="NASA benchmark dataset with RMSE metric and code https://github.com/nasa/example.",
                authors=json.dumps(["NASA"]),
                keywords=json.dumps(["neural operator", "hydrodynamics", "benchmark"]),
                item_type="technical report",
                published_at=datetime(2024, 1, 1),
                url="https://ntrs.nasa.gov/citations/nasa-1",
                pdf_url=None,
                fetched_at=datetime.utcnow(),
            )
        )
        session.commit()
    finally:
        session.close()

    created = client.post("/api/v1/scientist/tasks", json={"topic": "neural operator hydrodynamics", "use_llm": False})
    task_id = created.json()["id"]
    response = client.post(f"/api/v1/scientist/tasks/{task_id}/run?use_llm=false")

    assert response.status_code == 200
    data = response.json()
    assert any(item["source"] == "nasa" and item["understanding"] for item in data["items"])
    report = next(artifact for artifact in data["artifacts"] if artifact["kind"] == "report")
    assert "Top NASA Signals" in report["body_markdown"]
    assert "Paper Understanding Signals" in report["body_markdown"]

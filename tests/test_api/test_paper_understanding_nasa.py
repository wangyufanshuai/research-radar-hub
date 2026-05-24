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
from backend.collectors.nasa_collector import AdsCollector, NasaCollector
from backend.models.paper import Paper
from backend.repositories.nasa_item_repo import NasaItemRepository
from backend.services.paper_understanding import analyze_paper_by_id, extract_understanding_signals


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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_paper_understanding_extracts_rule_signals() -> None:
    text = (
        "We optimize L = mse(u, y) on the NASA CFD dataset. "
        "Code is available at https://github.com/example/neural-operator. "
        "We report RMSE and latency. Smith et al., 2024 improves [1, 2]."
    )

    signals = extract_understanding_signals(text)

    assert signals["code_mentions"] == ["https://github.com/example/neural-operator"]
    assert any("dataset" in item.lower() for item in signals["dataset_mentions"])
    assert any("rmse" in item.lower() for item in signals["metric_mentions"])
    assert signals["citation_mentions"]


def test_analyze_paper_api_falls_back_without_pdf(db_session, sample_paper_data, monkeypatch) -> None:
    paper = Paper(**sample_paper_data | {"abstract": "Dataset: CFD benchmark. Code: https://github.com/acme/cfd."})
    db_session.add(paper)
    db_session.commit()
    db_session.refresh(paper)

    result = analyze_paper_by_id(db_session, paper.id, allow_pdf=False)

    assert result.understanding_status == "metadata_only"
    assert "github.com/acme/cfd" in (result.code_mentions or "")
    assert result.paper_id == paper.id


def test_nasa_ntrs_collector_parses_mock_response(monkeypatch) -> None:
    payload = {
        "results": [
            {
                "id": "20240000001",
                "title": "Neural Operators for Spacecraft Thermal Simulation",
                "abstract": "A NASA study with benchmark data and code links.",
                "authors": [{"name": "A. Researcher"}],
                "keywords": ["neural operator", "simulation"],
                "publicationDate": "2024-05-01",
                "pdfUrl": "https://ntrs.nasa.gov/api/citations/20240000001/downloads/paper.pdf",
            }
        ]
    }

    collector = NasaCollector()
    monkeypatch.setattr(collector, "_fetch_with_retry", lambda *args, **kwargs: FakeResponse(payload))

    items = collector.collect(query="neural operator", max_results=1)

    assert items[0]["source"] == "ntrs"
    assert items[0]["source_id"] == "20240000001"
    assert items[0]["pdf_url"].endswith("paper.pdf")


def test_ads_collector_skips_without_token(monkeypatch) -> None:
    collector = AdsCollector()

    items = collector.collect(query="relativistic hydrodynamics", max_results=1)

    assert items == []


def test_collect_nasa_api_uses_mock_collector(client: TestClient, monkeypatch) -> None:
    from backend.services import collection

    class MockNasaCollector:
        def collect(self, **kwargs):
            return [
                {
                    "source": "ntrs",
                    "source_id": "mock-1",
                    "title": "NASA Neural Operator Benchmark",
                    "summary": "Benchmark dataset and RMSE metrics.",
                    "authors": json.dumps(["NASA"]),
                    "keywords": json.dumps(["neural operator"]),
                    "item_type": "technical report",
                    "published_at": datetime(2024, 1, 1),
                    "url": "https://ntrs.nasa.gov/citations/mock-1",
                    "pdf_url": None,
                    "fetched_at": datetime.utcnow(),
                }
            ]

        def collect_incremental(self, since, **kwargs):
            return self.collect(**kwargs)

        def close(self):
            return None

    old_entry = collection.COLLECTORS["nasa"]
    collection.COLLECTORS["nasa"] = (MockNasaCollector, NasaItemRepository, "source_id")
    try:
        response = client.post("/api/v1/collect/nasa")
    finally:
        collection.COLLECTORS["nasa"] = old_entry

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["records_fetched"] == 1

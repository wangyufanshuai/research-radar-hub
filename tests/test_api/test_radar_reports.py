from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base


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


def test_radar_endpoints_empty(client: TestClient) -> None:
    for path in ("/api/v1/radar/notices", "/api/v1/radar/changes", "/api/v1/radar/cves", "/api/v1/radar/courses"):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


def test_daily_report_endpoint_generates_report(client: TestClient) -> None:
    response = client.get("/api/v1/reports/daily?date=2026-05-19&kind=all&refresh=true")

    assert response.status_code == 200
    data = response.json()
    assert data["report_date"] == "2026-05-19"
    assert data["kind"] == "all"
    assert "学校公告" in data["body_markdown"]
    assert "CVE 漏洞情报" in data["body_markdown"]

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.collectors.course_collector import CourseCollector
from backend.core.config import CourseSourceConfig
from backend.models.course_item import CourseItem
from backend.models.paper import Paper
from backend.models.repo import Repo
from backend.services.research_radar import analyze_research_items, build_research_report_markdown


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


def test_research_radar_matches_paper_and_repo(client: TestClient) -> None:
    from backend.api.deps import get_db
    from backend.main import app

    session = next(app.dependency_overrides[get_db]())
    try:
        session.add(
            Paper(
                arxiv_id="2605.00001",
                title="Quantum gravity and holography in curved spacetime",
                abstract="We study general relativity and quantum field theory links.",
                authors=json.dumps(["A. Researcher"]),
                categories=json.dumps(["gr-qc", "hep-th"]),
                primary_category="gr-qc",
                published=datetime(2026, 5, 21, 8, 0, 0),
                fetched_at=datetime(2026, 5, 21, 8, 1, 0),
            )
        )
        session.add(
            Repo(
                github_id=123,
                full_name="example/pinn-surrogate-modeling",
                description="Physics-informed neural networks for surrogate modeling and digital twin simulation.",
                language="Python",
                stars=250,
                forks=20,
                open_issues=1,
                watchers=250,
                topics=json.dumps(["pinn", "surrogate-modeling"]),
                html_url="https://github.com/example/pinn-surrogate-modeling",
                pushed_at_gh=datetime(2026, 5, 21, 9, 0, 0),
                fetched_at=datetime(2026, 5, 21, 9, 1, 0),
            )
        )
        session.commit()

        items = analyze_research_items(session, date(2026, 5, 21), use_llm=False)
        assert {item.source for item in items} == {"arxiv", "github"}
        assert any(item.topic_key == "gr_qft" and item.score >= 6 for item in items)
        assert any(item.topic_key == "ai_engineering" and item.summary for item in items)
    finally:
        session.close()


def test_research_daily_report_endpoint_empty(client: TestClient) -> None:
    response = client.get("/api/v1/reports/daily?date=2026-05-21&kind=research&refresh=true")

    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "research"
    assert "No new research items" in data["body_markdown"]


def test_research_report_markdown_groups_items(client: TestClient) -> None:
    from backend.api.deps import get_db
    from backend.main import app

    session = next(app.dependency_overrides[get_db]())
    try:
        session.add(
            Paper(
                arxiv_id="2605.00002",
                title="Motion planning for robot learning",
                abstract="A robot learning method for manipulation and motion planning.",
                authors=json.dumps(["B. Researcher"]),
                categories=json.dumps(["cs.RO"]),
                primary_category="cs.RO",
                published=datetime(2026, 5, 21, 10, 0, 0),
                fetched_at=datetime(2026, 5, 21, 10, 1, 0),
            )
        )
        session.commit()
        body = build_research_report_markdown(session, date(2026, 5, 21), analyze=True, use_llm=False)
        assert "Robotics" in body
        assert "Motion planning for robot learning" in body
        assert "摘要:" in body
    finally:
        session.close()


def test_course_rss_collector_parses_feed(monkeypatch) -> None:
    source = CourseSourceConfig(
        id="mit-test",
        institution="MIT OpenCourseWare",
        url="https://example.edu/feed.xml",
        kind="rss",
        keywords=["robotics"],
    )
    collector = CourseCollector()

    class Response:
        text = """<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>Robotics and Motion Planning</title>
            <link>https://example.edu/robotics</link>
            <description>Robotics course with manipulation topics.</description>
            <pubDate>Thu, 21 May 2026 09:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""

    monkeypatch.setattr(collector, "_fetch_with_retry", lambda url: Response())
    items = collector._collect_rss(source)

    assert len(items) == 1
    assert items[0]["institution"] == "MIT OpenCourseWare"
    assert items[0]["title"] == "Robotics and Motion Planning"
    assert items[0]["published_at"].year == 2026


def test_course_html_collector_parses_links(monkeypatch) -> None:
    source = CourseSourceConfig(
        id="cambridge-test",
        institution="University of Cambridge",
        url="https://example.edu/courses",
        kind="html",
        selector="a",
        keywords=["engineering"],
        level="undergraduate",
    )
    collector = CourseCollector()

    class Response:
        text = """
        <html><body>
          <a href="/engineering">Engineering</a>
          <a href="/history">History</a>
        </body></html>
        """

    monkeypatch.setattr(collector, "_fetch_with_retry", lambda url: Response())
    items = collector._collect_html(source)

    assert len(items) == 1
    assert items[0]["title"] == "Engineering"
    assert items[0]["url"] == "https://example.edu/engineering"
    assert items[0]["level"] == "undergraduate"


def test_course_item_matches_research_report(client: TestClient) -> None:
    from backend.api.deps import get_db
    from backend.main import app

    session = next(app.dependency_overrides[get_db]())
    try:
        session.add(
            CourseItem(
                institution="ETH Zurich",
                source_id="eth-test",
                title="Robot Learning and Motion Planning",
                url="https://example.edu/eth/robot-learning",
                summary="A robotics course covering manipulation, robot learning, and motion planning.",
                department="Engineering",
                level="graduate",
                topics=json.dumps(["robot learning", "motion planning"]),
                published_at=None,
                first_seen_at=datetime(2026, 5, 21, 8, 0, 0),
                last_seen_at=datetime(2026, 5, 21, 8, 0, 0),
                content_hash="course-hash",
            )
        )
        session.commit()
        body = build_research_report_markdown(session, date(2026, 5, 21), analyze=True, use_llm=False)
        assert "Courses" in body
        assert "Robot Learning and Motion Planning" in body
        assert "Robotics" in body
    finally:
        session.close()


def test_courses_endpoint_lists_items(client: TestClient) -> None:
    from backend.api.deps import get_db
    from backend.main import app

    session = next(app.dependency_overrides[get_db]())
    try:
        session.add(
            CourseItem(
                institution="MIT OpenCourseWare",
                source_id="mit-test",
                title="Machine Learning for Engineering",
                url="https://example.edu/mit/ml-engineering",
                summary="Engineering applications of machine learning.",
                department="Engineering",
                level=None,
                topics=json.dumps(["machine learning", "engineering"]),
                published_at=datetime(2026, 5, 21, 9, 0, 0),
                first_seen_at=datetime(2026, 5, 21, 9, 0, 0),
                last_seen_at=datetime(2026, 5, 21, 9, 0, 0),
                content_hash="course-hash-2",
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/api/v1/radar/courses?institution=MIT%20OpenCourseWare")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Machine Learning for Engineering"


def test_course_source_registered_for_collection() -> None:
    from backend.services.collection import COLLECTORS

    assert "course" in COLLECTORS


def test_send_daily_report_uses_mock_sender(client: TestClient) -> None:
    sent = {}

    response = client.get("/api/v1/reports/daily?date=2026-05-21&kind=research&refresh=true")
    assert response.status_code == 200

    from backend.api.deps import get_db
    from backend.main import app
    from backend.repositories.daily_report_repo import DailyReportRepository
    from backend.services.email import send_daily_report_email

    session = next(app.dependency_overrides[get_db]())
    try:
        report = DailyReportRepository(session).get_by_date_kind(date(2026, 5, 21), "research")
        assert report is not None

        def fake_sender(subject: str, body_html: str, recipient: str) -> None:
            sent["subject"] = subject
            sent["body_html"] = body_html
            sent["recipient"] = recipient

        email_report = send_daily_report_email(session, report, sender=fake_sender)
        assert email_report.status == "sent"
        assert "Research Radar Daily" in sent["subject"]
        assert "<html" in sent["body_html"]
    finally:
        session.close()

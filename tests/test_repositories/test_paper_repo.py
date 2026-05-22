from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from backend.models.paper import Paper
from backend.repositories.paper_repo import PaperRepository


class TestPaperRepository:
    """Tests for PaperRepository upsert and search operations."""

    def test_upsert_new_paper(
        self, db_session: Session, sample_paper_data: dict
    ) -> None:
        repo = PaperRepository(db_session)
        paper = repo.upsert_by_field("arxiv_id", sample_paper_data["arxiv_id"], sample_paper_data)
        db_session.flush()

        assert paper.id is not None
        assert paper.arxiv_id == sample_paper_data["arxiv_id"]
        assert paper.title == sample_paper_data["title"]
        assert paper.primary_category == "cs.AI"

    def test_upsert_existing_paper(
        self, db_session: Session, sample_paper_data: dict
    ) -> None:
        repo = PaperRepository(db_session)
        repo.upsert_by_field("arxiv_id", sample_paper_data["arxiv_id"], sample_paper_data)
        db_session.flush()

        updated_data = copy.copy(sample_paper_data)
        updated_data["title"] = "Updated Title for Existing Paper"
        updated_data["abstract"] = "Updated abstract content."

        paper = repo.upsert_by_field("arxiv_id", updated_data["arxiv_id"], updated_data)
        db_session.flush()

        assert paper.title == "Updated Title for Existing Paper"
        assert paper.abstract == "Updated abstract content."
        assert paper.arxiv_id == sample_paper_data["arxiv_id"]

        # Verify only one record exists
        all_papers = db_session.query(Paper).all()
        assert len(all_papers) == 1

    def test_bulk_upsert(self, db_session: Session, sample_paper_data: dict) -> None:
        repo = PaperRepository(db_session)

        now = datetime.now(tz=timezone.utc)
        items = [
            {
                "arxiv_id": "2401.00001",
                "title": "First Paper on Transformers",
                "abstract": "Abstract one.",
                "authors": json.dumps(["Author A"]),
                "categories": json.dumps(["cs.AI"]),
                "primary_category": "cs.AI",
                "published": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                "fetched_at": now,
            },
            {
                "arxiv_id": "2401.00002",
                "title": "Second Paper on GANs",
                "abstract": "Abstract two.",
                "authors": json.dumps(["Author B"]),
                "categories": json.dumps(["cs.CV"]),
                "primary_category": "cs.CV",
                "published": datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                "fetched_at": now,
            },
            {
                "arxiv_id": "2401.00003",
                "title": "Third Paper on RL",
                "abstract": "Abstract three.",
                "authors": json.dumps(["Author C"]),
                "categories": json.dumps(["cs.LG"]),
                "primary_category": "cs.LG",
                "published": datetime(2024, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
                "fetched_at": now,
            },
        ]

        new_count, updated_count = repo.bulk_upsert("arxiv_id", items)

        assert new_count == 3
        assert updated_count == 0

        all_papers = db_session.query(Paper).all()
        assert len(all_papers) == 3

        # Bulk upsert again with one new and one updated
        items_update = [
            {
                "arxiv_id": "2401.00002",
                "title": "Updated Second Paper",
                "abstract": "Updated abstract two.",
                "authors": json.dumps(["Author B"]),
                "categories": json.dumps(["cs.CV"]),
                "primary_category": "cs.CV",
                "published": datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                "fetched_at": now,
            },
            {
                "arxiv_id": "2401.00004",
                "title": "Fourth Paper",
                "abstract": "Abstract four.",
                "authors": json.dumps(["Author D"]),
                "categories": json.dumps(["cs.AI"]),
                "primary_category": "cs.AI",
                "published": datetime(2024, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
                "fetched_at": now,
            },
        ]
        new_count2, updated_count2 = repo.bulk_upsert("arxiv_id", items_update)

        assert new_count2 == 1
        assert updated_count2 == 1

    def test_search_by_keyword(
        self, db_session: Session, sample_paper_data: dict
    ) -> None:
        repo = PaperRepository(db_session)
        repo.upsert_by_field("arxiv_id", sample_paper_data["arxiv_id"], sample_paper_data)

        now = datetime.now(tz=timezone.utc)
        second_paper = {
            "arxiv_id": "2401.00999",
            "title": "Reinforcement Learning for Robotics",
            "abstract": "A paper about robots and RL.",
            "authors": json.dumps(["Carol White"]),
            "categories": json.dumps(["cs.RO"]),
            "primary_category": "cs.RO",
            "published": datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
            "fetched_at": now,
        }
        repo.upsert_by_field("arxiv_id", second_paper["arxiv_id"], second_paper)
        db_session.flush()

        results = repo.search(keyword="Transformer")
        assert len(results) == 1
        assert results[0].arxiv_id == "2401.00001"

        # Case-insensitive match in abstract
        results_abstract = repo.search(keyword="novel")
        assert len(results_abstract) == 1

        # No match
        results_none = repo.search(keyword="quantum")
        assert len(results_none) == 0

    def test_search_by_category(
        self, db_session: Session, sample_paper_data: dict
    ) -> None:
        repo = PaperRepository(db_session)
        repo.upsert_by_field("arxiv_id", sample_paper_data["arxiv_id"], sample_paper_data)

        now = datetime.now(tz=timezone.utc)
        other_paper = {
            "arxiv_id": "2401.00888",
            "title": "Computer Vision Survey",
            "abstract": "Survey of CV methods.",
            "authors": json.dumps(["Dave Black"]),
            "categories": json.dumps(["cs.CV"]),
            "primary_category": "cs.CV",
            "published": datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
            "fetched_at": now,
        }
        repo.upsert_by_field("arxiv_id", other_paper["arxiv_id"], other_paper)
        db_session.flush()

        results = repo.search(category="cs.AI")
        assert len(results) == 1
        assert results[0].primary_category == "cs.AI"

        results_cv = repo.search(category="cs.CV")
        assert len(results_cv) == 1
        assert results_cv[0].arxiv_id == "2401.00888"

    def test_search_count(
        self, db_session: Session, sample_paper_data: dict
    ) -> None:
        repo = PaperRepository(db_session)
        repo.upsert_by_field("arxiv_id", sample_paper_data["arxiv_id"], sample_paper_data)

        now = datetime.now(tz=timezone.utc)
        extra_papers = [
            {
                "arxiv_id": f"2401.00{i}",
                "title": f"Paper number {i}",
                "abstract": f"Abstract {i}.",
                "authors": json.dumps(["Author"]),
                "categories": json.dumps(["cs.AI"]),
                "primary_category": "cs.AI",
                "published": datetime(2024, 1, i + 1, 0, 0, 0, tzinfo=timezone.utc),
                "fetched_at": now,
            }
            for i in range(2, 6)
        ]
        repo.bulk_upsert("arxiv_id", extra_papers)
        db_session.flush()

        total = repo.search_count()
        assert total == 5

        count_ai = repo.search_count(category="cs.AI")
        assert count_ai == 5

        count_keyword = repo.search_count(keyword="Transformer")
        assert count_keyword == 1

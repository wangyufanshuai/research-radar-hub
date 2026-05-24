from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import httpx
from sqlalchemy.orm import Session

from backend.core.config import get_config
from backend.models.nasa_item import NasaItem
from backend.models.paper import Paper
from backend.models.paper_understanding import PaperUnderstanding
from backend.repositories.nasa_item_repo import NasaItemRepository
from backend.repositories.paper_repo import PaperRepository
from backend.repositories.paper_understanding_repo import PaperUnderstandingRepository

logger = logging.getLogger(__name__)


@dataclass
class UnderstandingInput:
    paper_id: int | None
    source: str
    source_id: str
    title: str
    url: str | None
    pdf_url: str | None
    metadata_text: str


FORMULA_PATTERN = re.compile(r"(?:(?:[A-Za-z]\w*)\s*=|\\[a-zA-Z]+|[∂∇Σ∫≈≤≥]|[A-Za-z]\([^)]*\)\s*=)[^\n.;]{0,140}")
GITHUB_PATTERN = re.compile(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
DATASET_PATTERN = re.compile(
    r"\b(?:dataset|benchmark|corpus|data set|imagenet|mnist|cifar|mujoco|openml|kaggle|simulation data|synthetic data)\b[^.\n]{0,120}",
    re.I,
)
METRIC_PATTERN = re.compile(r"\b(?:accuracy|f1|auc|rmse|mae|mse|psnr|throughput|latency|runtime|memory|error rate)\b[^.\n]{0,120}", re.I)
CITATION_PATTERN = re.compile(r"(?:\[[0-9,\-\s]+\]|\b[A-Z][A-Za-z]+ et al\.,?\s+\d{4})")


def analyze_paper_by_id(db: Session, paper_id: int, allow_pdf: bool | None = None) -> PaperUnderstanding:
    paper = PaperRepository(db).get_by_id(paper_id)
    if paper is None:
        raise ValueError(f"Paper not found: {paper_id}")
    return analyze_understanding(db, _input_from_paper(paper), allow_pdf=allow_pdf)


def analyze_nasa_item(db: Session, nasa_item: NasaItem, allow_pdf: bool | None = None) -> PaperUnderstanding:
    return analyze_understanding(db, _input_from_nasa(nasa_item), allow_pdf=allow_pdf)


def analyze_understanding(db: Session, item: UnderstandingInput, allow_pdf: bool | None = None) -> PaperUnderstanding:
    config = get_config().paper_understanding
    should_fetch_pdf = config.download_pdfs if allow_pdf is None else allow_pdf
    status = "metadata_only"
    error_message = None
    pdf_text = ""

    if should_fetch_pdf and item.pdf_url:
        try:
            pdf_text = _extract_pdf_text(item.pdf_url)
            status = "pdf_analyzed" if pdf_text else "metadata_only"
        except Exception as exc:
            status = "pdf_failed"
            error_message = str(exc)
            logger.warning("[paper-understanding] PDF analysis failed for %s:%s: %s", item.source, item.source_id, exc)

    combined_text = "\n".join(part for part in [item.title, item.metadata_text, pdf_text] if part)
    signals = extract_understanding_signals(combined_text)
    data = {
        "paper_id": item.paper_id,
        "source": item.source,
        "source_id": item.source_id,
        "title": item.title,
        "url": item.url,
        "pdf_url": item.pdf_url,
        "text_excerpt": combined_text[: config.text_excerpt_chars],
        "formula_candidates": _json(signals["formula_candidates"]),
        "dataset_mentions": _json(signals["dataset_mentions"]),
        "code_mentions": _json(signals["code_mentions"]),
        "citation_mentions": _json(signals["citation_mentions"]),
        "metric_mentions": _json(signals["metric_mentions"]),
        "understanding_status": status,
        "error_message": error_message,
        "analyzed_at": datetime.utcnow(),
    }
    result = PaperUnderstandingRepository(db).upsert_understanding(data)
    db.commit()
    db.refresh(result)
    return result


def analyze_recent_papers(db: Session, limit: int = 20, allow_pdf: bool | None = None) -> list[PaperUnderstanding]:
    papers = PaperRepository(db).search(limit=limit)
    results = [analyze_paper_by_id(db, paper.id, allow_pdf=allow_pdf) for paper in papers]
    nasa_items = NasaItemRepository(db).recent(limit=limit)
    for item in nasa_items[: max(0, limit - len(results))]:
        results.append(analyze_nasa_item(db, item, allow_pdf=allow_pdf))
    return results


def extract_understanding_signals(text: str) -> dict[str, list[str]]:
    return {
        "formula_candidates": _unique(FORMULA_PATTERN.findall(text), limit=8),
        "dataset_mentions": _unique(DATASET_PATTERN.findall(text), limit=8),
        "code_mentions": _unique(GITHUB_PATTERN.findall(text), limit=8),
        "citation_mentions": _unique(CITATION_PATTERN.findall(text), limit=12),
        "metric_mentions": _unique(METRIC_PATTERN.findall(text), limit=8),
    }


def summarize_understandings(items: Iterable[PaperUnderstanding]) -> dict[str, list[str]]:
    merged = {
        "formula_candidates": [],
        "dataset_mentions": [],
        "code_mentions": [],
        "citation_mentions": [],
        "metric_mentions": [],
    }
    for item in items:
        for key in merged:
            merged[key].extend(_load_json_list(getattr(item, key)))
    return {key: _unique(values, limit=10) for key, values in merged.items()}


def _extract_pdf_text(url: str) -> str:
    config = get_config().paper_understanding
    with httpx.Client(timeout=config.timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            raise ValueError("URL did not return a PDF content type")
        if len(response.content) > config.max_pdf_bytes:
            raise ValueError("PDF exceeds configured max_pdf_bytes")
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("pypdf is not installed") from exc
        reader = PdfReader(io.BytesIO(response.content))
        page_count = min(len(reader.pages), config.max_pdf_pages)
        parts = []
        for page in reader.pages[:page_count]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)


def _input_from_paper(paper: Paper) -> UnderstandingInput:
    return UnderstandingInput(
        paper_id=paper.id,
        source="arxiv",
        source_id=paper.arxiv_id,
        title=paper.title,
        url=paper.entry_url or paper.pdf_url,
        pdf_url=paper.pdf_url,
        metadata_text="\n".join(part for part in [paper.abstract, paper.comment, paper.categories] if part),
    )


def _input_from_nasa(item: NasaItem) -> UnderstandingInput:
    return UnderstandingInput(
        paper_id=None,
        source=f"nasa:{item.source}",
        source_id=item.source_id,
        title=item.title,
        url=item.url,
        pdf_url=item.pdf_url,
        metadata_text="\n".join(part for part in [item.summary, item.keywords, item.authors] if part),
    )


def _json(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except Exception:
        return []


def _unique(values: Iterable[str], limit: int) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for raw in values:
        value = " ".join(str(raw).split()).strip(" .;,")
        key = value.lower()
        if len(value) < 2 or key in seen:
            continue
        seen.add(key)
        results.append(value)
        if len(results) >= limit:
            break
    return results

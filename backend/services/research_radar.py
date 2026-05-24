from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.config import ResearchTopicConfig, get_config, get_project_root, get_secrets
from backend.models.paper import Paper
from backend.models.course_item import CourseItem
from backend.models.repo import Repo
from backend.models.radar_item import RadarItem
from backend.repositories.radar_item_repo import RadarItemRepository


@dataclass
class MatchResult:
    topic_key: str
    topic_name: str
    score: float
    reason: str


def analyze_research_items(
    db: Session,
    report_date: date | None = None,
    use_llm: bool = True,
) -> list[RadarItem]:
    config = get_config().research_radar
    target_date = report_date or date.today()
    start, end = _report_window(target_date, config.lookback_days)
    topics = _configured_topics()
    repo = RadarItemRepository(db)
    analyzed: list[RadarItem] = []
    llm_remaining = max(0, config.llm_max_items_per_report)
    db.execute(
        delete(RadarItem).where(
            RadarItem.published_at >= start,
            RadarItem.published_at <= end,
        )
    )

    def summarize_with_budget(data: dict, source_text: str) -> dict:
        nonlocal llm_remaining
        should_use_llm = use_llm and llm_remaining > 0 and data["score"] >= config.min_score
        summary = _summarize(data, source_text, use_llm=should_use_llm)
        if should_use_llm:
            llm_remaining -= 1
        return summary

    for paper in _papers_for_window(db, start, end):
        for match in _match_paper(paper, topics):
            data = _radar_data_from_paper(paper, match)
            data.update(summarize_with_budget(data, paper.abstract or ""))
            data["include_in_report"] = match.score >= config.min_score
            analyzed.append(repo.upsert_item(data))

    for github_repo in _repos_for_window(db, start, end):
        for match in _match_repo(github_repo, topics):
            data = _radar_data_from_repo(github_repo, match)
            data.update(summarize_with_budget(data, github_repo.description or ""))
            data["include_in_report"] = match.score >= config.min_score
            analyzed.append(repo.upsert_item(data))

    for course in _courses_for_window(db, start, end):
        for match in _match_course(course, topics):
            data = _radar_data_from_course(course, match)
            data.update(summarize_with_budget(data, course.summary or ""))
            data["include_in_report"] = match.score >= config.min_score
            analyzed.append(repo.upsert_item(data))

    db.commit()
    return analyzed


def build_research_report_markdown(
    db: Session,
    report_date: date | None = None,
    analyze: bool = True,
    use_llm: bool = True,
) -> str:
    config = get_config().research_radar
    target_date = report_date or date.today()
    if analyze:
        analyze_research_items(db, target_date, use_llm=use_llm)

    start, end = _report_window(target_date, config.lookback_days)
    items = RadarItemRepository(db).list_for_report(start, end, limit=1000)
    grouped: dict[str, dict[str, list[RadarItem]]] = defaultdict(lambda: defaultdict(list))
    for item in items:
        grouped[item.topic_key][item.source].append(item)

    lines = [f"# Research Radar Daily - {target_date.isoformat()}"]
    if not items:
        lines.extend(["", "No new research items matched the configured topics."])
        return "\n".join(lines)

    topics = _configured_topics()
    for topic_key, topic in topics.items():
        source_groups = grouped.get(topic_key, {})
        if not source_groups:
            continue
        lines.extend(["", f"## {topic.name}"])
        for source in ("arxiv", "github", "course"):
            source_items = sorted(
                source_groups.get(source, []),
                key=lambda item: (item.score, item.value_score or 0),
                reverse=True,
            )[: config.max_items_per_topic_source]
            if not source_items:
                continue
            label = {
                "arxiv": "arXiv Papers",
                "github": "GitHub Projects",
                "course": "Courses",
            }[source]
            lines.extend(["", f"### {label}"])
            for item in source_items:
                value = f", value={item.value_score}/5" if item.value_score else ""
                lines.append(f"- [{item.title}]({item.url or ''}) (score={item.score:.1f}{value})")
                if item.summary:
                    lines.append(f"  - 摘要: {item.summary}")
                if item.reason:
                    lines.append(f"  - 推荐理由: {item.reason}")
    return "\n".join(lines)


def markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown

        body = markdown.markdown(markdown_text, extensions=["extra"])
    except Exception:
        body = f"<pre>{html.escape(markdown_text)}</pre>"
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;line-height:1.55;"
        "max-width:900px;margin:24px auto;color:#1f2937}a{color:#2563eb}"
        "h1,h2,h3{color:#111827}li{margin:8px 0}</style></head><body>"
        f"{body}</body></html>"
    )


def write_report_html(markdown_text: str, report_date: date | None = None) -> Path:
    config = get_config().research_radar
    target_date = report_date or date.today()
    output_dir = get_project_root() / config.output_directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"research_radar_{target_date.isoformat()}.html"
    output_path.write_text(markdown_to_html(markdown_text), encoding="utf-8")
    return output_path


def _configured_topics() -> dict[str, ResearchTopicConfig]:
    configured = get_config().research_radar.topics
    if configured:
        return configured
    return {
        "gr_qft": ResearchTopicConfig(
            name="GR/QFT",
            categories=["gr-qc", "hep-th"],
            keywords=["quantum gravity", "general relativity", "qft", "holography"],
        ),
        "ai_engineering": ResearchTopicConfig(
            name="AI for Engineering",
            categories=["cs.AI", "cs.LG", "stat.ML"],
            keywords=["surrogate modeling", "pinn", "digital twin", "simulation ai"],
        ),
        "cae": ResearchTopicConfig(
            name="CAE",
            keywords=["finite element", "computational mechanics", "topology optimization", "multiphysics"],
        ),
        "robotics": ResearchTopicConfig(
            name="Robotics",
            categories=["cs.RO"],
            keywords=["robot learning", "motion planning", "slam", "manipulation"],
        ),
        "cybersecurity": ResearchTopicConfig(
            name="Cybersecurity",
            categories=["cs.CR"],
            keywords=["vulnerability", "malware", "fuzzing", "secure systems"],
        ),
    }


def _report_window(target_date: date, lookback_days: int) -> tuple[datetime, datetime]:
    days = max(1, lookback_days)
    start_date = target_date - timedelta(days=days - 1)
    return datetime.combine(start_date, time.min), datetime.combine(target_date, time.max)


def _papers_for_window(db: Session, start: datetime, end: datetime) -> Iterable[Paper]:
    stmt = select(Paper).where(Paper.published >= start, Paper.published <= end)
    return db.execute(stmt.order_by(Paper.published.desc())).scalars().all()


def _repos_for_window(db: Session, start: datetime, end: datetime) -> Iterable[Repo]:
    stmt = select(Repo).where(Repo.pushed_at_gh >= start, Repo.pushed_at_gh <= end)
    return db.execute(stmt.order_by(Repo.stars.desc())).scalars().all()


def _courses_for_window(db: Session, start: datetime, end: datetime) -> Iterable[CourseItem]:
    stmt = select(CourseItem).where(
        CourseItem.last_seen_at >= start,
        CourseItem.last_seen_at <= end,
    )
    return db.execute(stmt.order_by(CourseItem.last_seen_at.desc())).scalars().all()


def _match_paper(paper: Paper, topics: dict[str, ResearchTopicConfig]) -> list[MatchResult]:
    text = f"{paper.title} {paper.abstract or ''}".lower()
    categories = _json_list(paper.categories)
    if paper.primary_category:
        categories.append(paper.primary_category)
    results = []
    for key, topic in topics.items():
        keyword_hits = _keyword_hits(text, topic.keywords)
        category_hits = sorted({cat for cat in categories if cat in topic.categories})
        score = float(len(keyword_hits) * 2 + len(category_hits) * 3)
        if score > 0:
            reason_parts = []
            if category_hits:
                reason_parts.append("categories: " + ", ".join(category_hits))
            if keyword_hits:
                reason_parts.append("keywords: " + ", ".join(keyword_hits[:5]))
            results.append(MatchResult(key, topic.name, score, "; ".join(reason_parts)))
    return sorted(results, key=lambda match: match.score, reverse=True)


def _match_repo(repo: Repo, topics: dict[str, ResearchTopicConfig]) -> list[MatchResult]:
    repo_topics = _json_list(repo.topics)
    text = f"{repo.full_name} {repo.description or ''} {' '.join(repo_topics)}".lower()
    results = []
    for key, topic in topics.items():
        keyword_hits = _keyword_hits(text, topic.keywords)
        topic_hits = _keyword_hits(text, topic.categories)
        if not keyword_hits and not topic_hits:
            continue
        star_bonus = min(repo.stars / 500.0, 3.0)
        score = float(len(keyword_hits) * 2 + len(topic_hits) + star_bonus)
        reason_parts = []
        if keyword_hits:
            reason_parts.append("keywords: " + ", ".join(keyword_hits[:5]))
        if topic_hits:
            reason_parts.append("topics: " + ", ".join(topic_hits[:5]))
        if repo.stars:
            reason_parts.append(f"stars: {repo.stars}")
        results.append(MatchResult(key, topic.name, score, "; ".join(reason_parts)))
    return sorted(results, key=lambda match: match.score, reverse=True)


def _match_course(course: CourseItem, topics: dict[str, ResearchTopicConfig]) -> list[MatchResult]:
    course_topics = _json_list(course.topics)
    text = (
        f"{course.title} {course.summary or ''} {course.department or ''} "
        f"{course.level or ''} {' '.join(course_topics)}"
    ).lower()
    results = []
    for key, topic in topics.items():
        keyword_hits = _keyword_hits(text, topic.keywords)
        category_hits = _keyword_hits(text, topic.categories)
        score = float(len(keyword_hits) * 2 + len(category_hits))
        if score > 0:
            reason_parts = []
            if keyword_hits:
                reason_parts.append("keywords: " + ", ".join(keyword_hits[:5]))
            if course.institution:
                reason_parts.append(f"institution: {course.institution}")
            results.append(MatchResult(key, topic.name, score, "; ".join(reason_parts)))
    return sorted(results, key=lambda match: match.score, reverse=True)


def _radar_data_from_paper(paper: Paper, match: MatchResult) -> dict:
    return {
        "source": "arxiv",
        "source_id": paper.arxiv_id,
        "source_table_id": paper.id,
        "topic_key": match.topic_key,
        "topic_name": match.topic_name,
        "title": paper.title,
        "url": paper.entry_url or paper.pdf_url,
        "published_at": paper.published,
        "score": match.score,
        "reason": match.reason,
        "analyzed_at": datetime.utcnow(),
    }


def _radar_data_from_repo(repo: Repo, match: MatchResult) -> dict:
    return {
        "source": "github",
        "source_id": str(repo.github_id),
        "source_table_id": repo.id,
        "topic_key": match.topic_key,
        "topic_name": match.topic_name,
        "title": repo.full_name,
        "url": repo.html_url,
        "published_at": repo.pushed_at_gh or repo.updated_at_gh or datetime.utcnow(),
        "score": match.score,
        "reason": match.reason,
        "analyzed_at": datetime.utcnow(),
    }


def _radar_data_from_course(course: CourseItem, match: MatchResult) -> dict:
    return {
        "source": "course",
        "source_id": str(course.id),
        "source_table_id": course.id,
        "topic_key": match.topic_key,
        "topic_name": match.topic_name,
        "title": course.title,
        "url": course.url,
        "published_at": course.published_at or course.first_seen_at,
        "score": match.score,
        "reason": match.reason,
        "analyzed_at": datetime.utcnow(),
    }


def _summarize(data: dict, source_text: str, use_llm: bool) -> dict:
    fallback = {
        "summary": _fallback_summary(source_text),
        "reason": data.get("reason"),
        "value_score": min(5, max(1, int(round(data["score"] / 2)))),
    }
    secrets = get_secrets()
    if not use_llm or not secrets.openai_api_key:
        return fallback
    try:
        return _openai_summary(
            data,
            source_text,
            api_key=secrets.openai_api_key,
            base_url=secrets.openai_base_url,
            model=secrets.openai_model,
        )
    except Exception:
        return fallback


def _openai_summary(data: dict, source_text: str, api_key: str, base_url: str, model: str) -> dict:
    prompt = (
        "Summarize this research radar item in Chinese. Return strict JSON with "
        "summary, reason, value_score where value_score is an integer 1-5.\n"
        f"Title: {data['title']}\nSource: {data['source']}\nMatched reason: {data.get('reason')}\n"
        f"Text: {source_text[:3000]}"
    )
    endpoint = base_url.rstrip("/") + "/chat/completions"
    response = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=20,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    payload = _extract_json(content)
    return {
        "summary": str(payload.get("summary") or _fallback_summary(source_text)),
        "reason": str(payload.get("reason") or data.get("reason") or ""),
        "value_score": int(payload.get("value_score") or 3),
    }


def _extract_json(content: str) -> dict:
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        return {}
    return json.loads(match.group(0))


def _fallback_summary(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "暂无摘要。"
    return cleaned[:260] + ("..." if len(cleaned) > 260 else "")


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    hits = []
    for keyword in keywords:
        key = keyword.lower()
        if key and key in text:
            hits.append(keyword)
    return hits


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return [str(item) for item in parsed if item]
    except Exception:
        return [item.strip() for item in value.split(",") if item.strip()]

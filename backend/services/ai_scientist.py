from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.collectors.arxiv_collector import ArxivCollector
from backend.collectors.github_collector import GitHubCollector
from backend.collectors.nasa_collector import NasaCollector
from backend.core.config import get_project_root, get_secrets
from backend.models.nasa_item import NasaItem
from backend.models.paper import Paper
from backend.models.repo import Repo
from backend.models.paper_understanding import PaperUnderstanding
from backend.models.scientist import ScientistArtifact, ScientistRun, ScientistTask
from backend.repositories.nasa_item_repo import NasaItemRepository
from backend.repositories.paper_repo import PaperRepository
from backend.repositories.repo_repo import RepoRepository
from backend.repositories.scientist_repo import (
    ScientistTaskItemRepository,
    ScientistTaskRepository,
)
from backend.services.paper_understanding import analyze_nasa_item, analyze_paper_by_id, summarize_understandings
from backend.services.research_radar import markdown_to_html

logger = logging.getLogger(__name__)

STAGES = ("Planner", "Scout", "Deduplicator", "NoveltyScorer", "Reproducer", "Writer")


@dataclass
class PlannedQuery:
    topic: str
    keywords: list[str]
    arxiv_query: str
    github_query: str


def create_scientist_task(db: Session, topic: str) -> ScientistTask:
    task = ScientistTask(topic=topic.strip(), status="created")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_scientist_task(
    db: Session,
    task_id: int,
    max_papers: int = 20,
    max_repos: int = 10,
    use_llm: bool = True,
) -> ScientistTask:
    task_repo = ScientistTaskRepository(db)
    task = task_repo.get_by_id(task_id)
    if task is None:
        raise ValueError(f"Scientist task not found: {task_id}")

    task.status = "running"
    task.error_message = None
    db.commit()

    try:
        plan = _stage(db, task, "Planner", lambda: plan_query(task.topic))
        task.query = json.dumps(plan.__dict__, ensure_ascii=False)
        db.commit()

        raw_items = _stage(db, task, "Scout", lambda: scout_candidates(db, plan, max_papers, max_repos))
        deduped = _stage(db, task, "Deduplicator", lambda: deduplicate_items(raw_items))
        scored = _stage(db, task, "NoveltyScorer", lambda: score_items(db, deduped, plan))
        saved_items = ScientistTaskItemRepository(db).replace_task_items(task.id, scored)
        _attach_understandings(db, saved_items)
        db.commit()

        reading_route, experiment_plan = _stage(
            db,
            task,
            "Reproducer",
            lambda: build_reproduction_artifacts(task, saved_items, plan, use_llm=use_llm),
        )
        report = _stage(
            db,
            task,
            "Writer",
            lambda: write_scientist_report(task, saved_items, plan, reading_route, experiment_plan),
        )
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        logger.info("[ai-scientist] Wrote report for task %s to %s", task.id, report.html_path)
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        db.commit()
        raise

    refreshed = task_repo.get_detail(task.id)
    return refreshed or task


def plan_query(topic: str) -> PlannedQuery:
    cleaned = " ".join(topic.split())
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", cleaned)
        if token.lower() not in {"for", "with", "and", "the", "using", "from"}
    ]
    phrases = _key_phrases(cleaned)
    keywords = []
    for value in [cleaned, *phrases, *tokens]:
        value = value.strip().lower()
        if value and value not in keywords:
            keywords.append(value)
    arxiv_query = " OR ".join(f'all:"{phrase}"' for phrase in keywords[:6])
    github_query = " ".join(keywords[:5])
    return PlannedQuery(topic=cleaned, keywords=keywords[:12], arxiv_query=arxiv_query, github_query=github_query)


def scout_candidates(db: Session, plan: PlannedQuery, max_papers: int, max_repos: int) -> list[dict]:
    _try_collect_arxiv(db, plan, max_papers)
    _try_collect_github(db, plan, max_repos)
    _try_collect_nasa(db, plan, max_papers)
    _ensure_fts(db)

    paper_rows = _search_papers(db, plan, max_papers)
    repo_rows = _search_repos(db, plan, max_repos)
    nasa_rows = _search_nasa_items(db, plan, max_papers)
    rows = [*_paper_items(paper_rows), *_repo_items(repo_rows), *_nasa_items(nasa_rows)]
    _refresh_fts(db, rows)
    return rows


def deduplicate_items(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    results: list[dict] = []
    for item in sorted(items, key=lambda row: row.get("published_at") or "", reverse=True):
        key = _normalize_title(item["title"])
        identity = f"{item['source']}:{item['source_id']}"
        if key in seen or identity in seen:
            continue
        seen.add(key)
        seen.add(identity)
        results.append(item)
    return results


def score_items(db: Session, items: list[dict], plan: PlannedQuery) -> list[dict]:
    normalized_titles = [_normalize_title(item["title"]) for item in items]
    scored: list[dict] = []
    for item, normalized in zip(items, normalized_titles):
        text_blob = f"{item['title']} {item.get('summary') or ''} {item.get('topics') or ''}".lower()
        keyword_hits = [keyword for keyword in plan.keywords if keyword in text_blob]
        relevance = min(10.0, 2.0 + len(keyword_hits) * 1.5 + _term_overlap(plan.topic, text_blob) * 4.0)
        near_duplicates = sum(1 for title in normalized_titles if title != normalized and _jaccard(title, normalized) > 0.65)
        recency_bonus = _recency_bonus(item.get("published_at"))
        novelty = max(1.0, min(10.0, 5.0 + recency_bonus + len(keyword_hits) * 0.5 - near_duplicates))
        understanding = _understanding_for_item(db, item)
        reproducibility = _reproducibility_score(item, understanding)
        selected = relevance >= 3.0 and (item["source"] == "github" or novelty >= 4.0)
        scored.append(
            {
                "source": item["source"],
                "source_id": str(item["source_id"]),
                "title": item["title"],
                "url": item.get("url"),
                "summary": item.get("summary"),
                "relevance_score": round(relevance, 2),
                "novelty_score": round(novelty, 2),
                "reproducibility_score": round(reproducibility, 2),
                "selected": selected,
            }
        )
    return sorted(
        scored,
        key=lambda row: (row["selected"], row["relevance_score"], row["novelty_score"], row["reproducibility_score"]),
        reverse=True,
    )


def build_reproduction_artifacts(
    task: ScientistTask,
    items: Iterable,
    plan: PlannedQuery,
    use_llm: bool = True,
) -> tuple[ScientistArtifact, ScientistArtifact]:
    selected = [item for item in items if item.selected]
    understandings = _understandings_for_task_items(selected)
    reading_body = _build_reading_route(task.topic, selected, plan)
    experiment_body = _build_experiment_plan(task.topic, selected, plan, understandings)
    if use_llm:
        reading_body, experiment_body = _llm_enhance_plan(task.topic, selected, reading_body, experiment_body)

    now = datetime.utcnow()
    reading = ScientistArtifact(
        task_id=task.id,
        kind="reading_route",
        title=f"Reading route: {task.topic}",
        body_markdown=reading_body,
        created_at_artifact=now,
    )
    experiment = ScientistArtifact(
        task_id=task.id,
        kind="experiment_plan",
        title=f"Reproduction plan: {task.topic}",
        body_markdown=experiment_body,
        created_at_artifact=now,
    )
    return reading, experiment


def write_scientist_report(
    task: ScientistTask,
    items: Iterable,
    plan: PlannedQuery,
    reading_route: ScientistArtifact,
    experiment_plan: ScientistArtifact,
) -> ScientistArtifact:
    selected = [item for item in items if item.selected]
    papers = [item for item in selected if item.source == "arxiv"][:10]
    repos = [item for item in selected if item.source == "github"][:6]
    nasa_items = [item for item in selected if item.source == "nasa"][:8]
    signals = summarize_understandings(_understandings_for_task_items(selected))
    lines = [
        f"# AI Scientist Report - {task.topic}",
        "",
        "## Query Strategy",
        f"- Topic: {task.topic}",
        f"- arXiv query: `{plan.arxiv_query}`",
        f"- GitHub query: `{plan.github_query}`",
        f"- Keywords: {', '.join(plan.keywords)}",
        "",
        "## Top Papers",
    ]
    lines.extend(_item_lines(papers) or ["No matching papers were selected."])
    lines.extend(["", "## Top GitHub Repositories"])
    lines.extend(_item_lines(repos) or ["No matching repositories were selected."])
    lines.extend(["", "## Top NASA Signals"])
    lines.extend(_item_lines(nasa_items) or ["No matching NASA items were selected."])
    lines.extend(["", "## Novelty Assessment", _novelty_summary(selected)])
    lines.extend(["", "## Paper Understanding Signals"])
    lines.extend(_signal_lines("Formula candidates", signals["formula_candidates"]))
    lines.extend(_signal_lines("Datasets / Benchmarks", signals["dataset_mentions"]))
    lines.extend(_signal_lines("Code Availability", signals["code_mentions"]))
    lines.extend(_signal_lines("Citation Clues", signals["citation_mentions"]))
    lines.extend(_signal_lines("Metrics", signals["metric_mentions"]))
    lines.extend(["", reading_route.body_markdown, "", experiment_plan.body_markdown])
    lines.extend(
        [
            "",
            "## Risks and Gaps",
            "- This MVP uses metadata and abstracts only; PDF-level formula and table extraction is not included.",
            "- External repository code is not executed automatically.",
            "- Novelty scoring is heuristic and should be reviewed before research decisions.",
            "",
            "## Next Steps",
            "- Manually inspect the top 3 papers and any linked repositories.",
            "- Convert the reproduction plan into a reviewed notebook before running experiments.",
            "- Add PDF parsing and citation graph scoring in the next version.",
        ]
    )
    body = "\n".join(lines)
    output_dir = get_project_root() / "reports" / "scientist"
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"scientist_task_{task.id}.md"
    html_path = output_dir / f"scientist_task_{task.id}.html"
    md_path.write_text(body, encoding="utf-8")
    html_path.write_text(markdown_to_html(body), encoding="utf-8")
    return ScientistArtifact(
        task_id=task.id,
        kind="report",
        title=f"AI Scientist Report - {task.topic}",
        body_markdown=body,
        html_path=str(html_path),
        created_at_artifact=datetime.utcnow(),
    )


def persist_artifacts(db: Session, artifacts: Iterable[ScientistArtifact]) -> None:
    for artifact in artifacts:
        db.add(artifact)
    db.commit()


def _stage(db: Session, task: ScientistTask, stage: str, fn):
    run = ScientistRun(task_id=task.id, stage=stage, status="running", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    try:
        result = fn()
        if stage == "Reproducer":
            persist_artifacts(db, result)
        elif stage == "Writer":
            persist_artifacts(db, [result])
        run.status = "success"
        run.message = _stage_message(stage, result)
        run.finished_at = datetime.utcnow()
        db.commit()
        return result
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.utcnow()
        db.commit()
        raise


def _stage_message(stage: str, result) -> str:
    if isinstance(result, list):
        return f"{stage} produced {len(result)} items."
    if isinstance(result, PlannedQuery):
        return f"{stage} planned {len(result.keywords)} keywords."
    if isinstance(result, tuple):
        return f"{stage} produced {len(result)} artifacts."
    return f"{stage} completed."


def _try_collect_arxiv(db: Session, plan: PlannedQuery, max_papers: int) -> None:
    collector = ArxivCollector()
    try:
        items = collector.collect(query=plan.arxiv_query, max_results=min(max_papers, 20), sort_by="relevance")
        PaperRepository(db).bulk_upsert("arxiv_id", items)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("[ai-scientist] arXiv scout failed, using existing data: %s", exc)
    finally:
        collector.close()


def _try_collect_github(db: Session, plan: PlannedQuery, max_repos: int) -> None:
    collector = GitHubCollector()
    try:
        items = collector.collect(query=plan.github_query, max_results=min(max_repos, 10), min_stars=10)
        RepoRepository(db).bulk_upsert("github_id", items)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("[ai-scientist] GitHub scout failed, using existing data: %s", exc)
    finally:
        collector.close()


def _try_collect_nasa(db: Session, plan: PlannedQuery, max_items: int) -> None:
    collector = NasaCollector()
    try:
        items = collector.collect(query=plan.topic, max_results=min(max_items, 20))
        NasaItemRepository(db).upsert_items(items)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("[ai-scientist] NASA scout failed, using existing data: %s", exc)
    finally:
        collector.close()


def _search_papers(db: Session, plan: PlannedQuery, limit: int) -> list[Paper]:
    terms = plan.keywords[:8]
    papers = PaperRepository(db).search(limit=500)
    ranked = sorted(
        papers,
        key=lambda paper: _term_overlap(" ".join(terms), f"{paper.title} {paper.abstract or ''}".lower()),
        reverse=True,
    )
    return [paper for paper in ranked if _term_overlap(" ".join(terms), f"{paper.title} {paper.abstract or ''}".lower()) > 0][:limit]


def _search_repos(db: Session, plan: PlannedQuery, limit: int) -> list[Repo]:
    repos = RepoRepository(db).search(limit=500)
    ranked = sorted(
        repos,
        key=lambda repo: (
            _term_overlap(" ".join(plan.keywords[:8]), f"{repo.full_name} {repo.description or ''} {repo.topics or ''}".lower()),
            repo.stars,
        ),
        reverse=True,
    )
    return [
        repo
        for repo in ranked
        if _term_overlap(" ".join(plan.keywords[:8]), f"{repo.full_name} {repo.description or ''} {repo.topics or ''}".lower()) > 0
    ][:limit]


def _search_nasa_items(db: Session, plan: PlannedQuery, limit: int) -> list[NasaItem]:
    items = NasaItemRepository(db).search(limit=500)
    ranked = sorted(
        items,
        key=lambda item: _term_overlap(" ".join(plan.keywords[:8]), f"{item.title} {item.summary or ''} {item.keywords or ''}".lower()),
        reverse=True,
    )
    return [
        item
        for item in ranked
        if _term_overlap(" ".join(plan.keywords[:8]), f"{item.title} {item.summary or ''} {item.keywords or ''}".lower()) > 0
    ][:limit]


def _paper_items(papers: Iterable[Paper]) -> list[dict]:
    return [
        {
            "source": "arxiv",
            "source_id": paper.arxiv_id,
            "title": paper.title,
            "url": paper.entry_url or paper.pdf_url,
            "summary": paper.abstract,
            "published_at": paper.published,
            "topics": paper.categories,
        }
        for paper in papers
    ]


def _nasa_items(items: Iterable[NasaItem]) -> list[dict]:
    return [
        {
            "source": "nasa",
            "source_id": f"{item.source}:{item.source_id}",
            "title": item.title,
            "url": item.url,
            "summary": item.summary,
            "published_at": item.published_at,
            "topics": item.keywords,
            "pdf_url": item.pdf_url,
            "nasa_source": item.source,
        }
        for item in items
    ]


def _repo_items(repos: Iterable[Repo]) -> list[dict]:
    return [
        {
            "source": "github",
            "source_id": str(repo.github_id),
            "title": repo.full_name,
            "url": repo.html_url,
            "summary": repo.description,
            "published_at": repo.pushed_at_gh or repo.updated_at_gh,
            "topics": repo.topics,
            "stars": repo.stars,
            "language": repo.language,
        }
        for repo in repos
    ]


def _ensure_fts(db: Session) -> None:
    db.execute(
        text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS scientist_search_fts "
            "USING fts5(task_key, source, source_id, title, body)"
        )
    )
    db.commit()


def _refresh_fts(db: Session, rows: list[dict]) -> None:
    for row in rows:
        db.execute(
            text(
                "INSERT INTO scientist_search_fts(task_key, source, source_id, title, body) "
                "VALUES (:task_key, :source, :source_id, :title, :body)"
            ),
            {
                "task_key": "latest",
                "source": row["source"],
                "source_id": str(row["source_id"]),
                "title": row["title"],
                "body": row.get("summary") or "",
            },
        )
    db.commit()


def _build_reading_route(topic: str, items: list, plan: PlannedQuery) -> str:
    top_papers = [item for item in items if item.source == "arxiv"][:6]
    lines = ["## Reading Route"]
    if not top_papers:
        return "\n".join([*lines, "No paper candidates were selected. Start by broadening the topic query."])
    lines.extend(
        [
            "1. Start with the newest high-relevance survey or method paper.",
            "2. Compare assumptions, datasets, metrics, and code availability.",
            "3. Read implementation-linked repositories after the first pass.",
            "",
            "Recommended order:",
        ]
    )
    for index, item in enumerate(top_papers, start=1):
        lines.append(f"{index}. [{item.title}]({item.url or ''}) - relevance {item.relevance_score:.1f}, novelty {item.novelty_score:.1f}")
    return "\n".join(lines)


def _build_experiment_plan(topic: str, items: list, plan: PlannedQuery, understandings: list[PaperUnderstanding] | None = None) -> str:
    repos = [item for item in items if item.source == "github"][:3]
    papers = [item for item in items if item.source == "arxiv"][:3]
    nasa_items = [item for item in items if item.source == "nasa"][:3]
    signals = summarize_understandings(understandings or [])
    lines = [
        "## Reproduction Experiment Plan",
        "### Objective",
        f"Reproduce a minimal baseline related to `{topic}` using public metadata first, then manually review papers/code before execution.",
        "",
        "### Candidate Baselines",
    ]
    if papers:
        lines.extend([f"- Paper baseline: [{item.title}]({item.url or ''})" for item in papers])
    if repos:
        lines.extend([f"- Code candidate: [{item.title}]({item.url or ''})" for item in repos])
    if nasa_items:
        lines.extend([f"- NASA signal: [{item.title}]({item.url or ''})" for item in nasa_items])
    if not papers and not repos:
        lines.append("- No selected baseline yet; expand the query or lower selection thresholds.")
    lines.extend(["", "### Extracted Signals"])
    lines.extend(_signal_lines("Datasets / benchmarks", signals["dataset_mentions"], empty="- No dataset signal extracted yet."))
    lines.extend(_signal_lines("Metrics", signals["metric_mentions"], empty="- No metric signal extracted yet."))
    lines.extend(_signal_lines("Code links", signals["code_mentions"], empty="- No code link extracted yet."))
    lines.extend(
        [
            "",
            "### Environment",
            "- Create an isolated Python environment.",
            "- Pin dependencies after manual repository inspection.",
            "- Do not run external install scripts without review.",
            "",
            "### Metrics",
            "- Reproduce the paper's primary metric when available.",
            "- Track runtime, memory, dataset size, and qualitative failure cases.",
            "",
            "### Steps",
            "1. Read the top 3 papers and record assumptions.",
            "2. Identify dataset availability and preprocessing requirements.",
            "3. Implement or adapt the simplest baseline.",
            "4. Run a smoke test on a small synthetic or sample dataset.",
            "5. Write results, deviations, and blockers into the experiment log.",
        ]
    )
    return "\n".join(lines)


def _llm_enhance_plan(topic: str, items: list, reading_body: str, experiment_body: str) -> tuple[str, str]:
    secrets = get_secrets()
    if not secrets.openai_api_key:
        return reading_body, experiment_body
    context = "\n".join(f"- {item.source}: {item.title}: {item.summary or ''}" for item in items[:8])
    prompt = (
        "You are improving an AI Scientist workspace report. Return strict JSON with keys "
        "reading_route and experiment_plan. Use concise Chinese headings and keep all safety limits: "
        "do not execute unknown code, do not claim PDF parsing was done.\n"
        f"Topic: {topic}\nCandidates:\n{context[:6000]}\n"
        f"Current reading route:\n{reading_body}\nCurrent experiment plan:\n{experiment_body}"
    )
    try:
        response = httpx.post(
            secrets.openai_base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {secrets.openai_api_key}"},
            json={
                "model": secrets.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.S)
        payload = json.loads(match.group(0)) if match else {}
        return str(payload.get("reading_route") or reading_body), str(payload.get("experiment_plan") or experiment_body)
    except Exception as exc:
        logger.warning("[ai-scientist] LLM enhancement failed, using fallback: %s", exc)
        return reading_body, experiment_body


def _item_lines(items: list) -> list[str]:
    return [
        (
            f"- [{item.title}]({item.url or ''}) "
            f"(relevance={item.relevance_score:.1f}, novelty={item.novelty_score:.1f}, "
            f"repro={item.reproducibility_score:.1f})"
        )
        for item in items
    ]


def _novelty_summary(items: list) -> str:
    if not items:
        return "No selected candidates were available for novelty scoring."
    avg = sum(item.novelty_score for item in items) / len(items)
    return f"Average selected novelty score: {avg:.1f}/10. Higher scores indicate recent, topic-specific candidates with fewer near-duplicates."


def _key_phrases(topic: str) -> list[str]:
    parts = re.split(r"\bfor\b|\bwith\b|\band\b|,", topic, flags=re.I)
    return [part.strip() for part in parts if len(part.strip()) > 4]


def _normalize_title(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def _term_overlap(query: str, text_blob: str) -> float:
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    text_terms = set(re.findall(r"[a-z0-9]+", text_blob.lower()))
    if not query_terms or not text_terms:
        return 0.0
    return len(query_terms & text_terms) / len(query_terms)


def _jaccard(left: str, right: str) -> float:
    left_terms = set(left.split())
    right_terms = set(right.split())
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def _recency_bonus(value) -> float:
    if not isinstance(value, datetime):
        return 0.0
    age_days = max(0, (datetime.utcnow() - value.replace(tzinfo=None)).days)
    return max(0.0, 2.0 - math.log10(age_days + 1))


def _understanding_for_item(db: Session, item: dict) -> PaperUnderstanding | None:
    try:
        if item["source"] == "arxiv":
            paper = PaperRepository(db).get_by_field("arxiv_id", item["source_id"])
            if paper:
                return analyze_paper_by_id(db, paper.id, allow_pdf=False)
        if item["source"] == "nasa":
            nasa_source, _, nasa_id = str(item["source_id"]).partition(":")
            nasa_item = NasaItemRepository(db).get_by_source_identity(nasa_source, nasa_id)
            if nasa_item:
                return analyze_nasa_item(db, nasa_item, allow_pdf=False)
    except Exception as exc:
        logger.warning("[ai-scientist] Paper understanding failed for %s:%s: %s", item.get("source"), item.get("source_id"), exc)
    return None


def _understandings_for_task_items(items: Iterable) -> list[PaperUnderstanding]:
    results: list[PaperUnderstanding] = []
    for item in items:
        understanding = getattr(item, "understanding", None)
        if understanding is not None:
            results.append(understanding)
    return results


def _attach_understandings(db: Session, items: Iterable) -> None:
    from backend.repositories.paper_understanding_repo import PaperUnderstandingRepository

    repo = PaperUnderstandingRepository(db)
    for item in items:
        understanding = None
        if item.source == "arxiv":
            understanding = repo.get_by_source_identity("arxiv", item.source_id)
        elif item.source == "nasa":
            nasa_source, _, nasa_id = item.source_id.partition(":")
            if nasa_source and nasa_id:
                understanding = repo.get_by_source_identity(f"nasa:{nasa_source}", nasa_id)
        try:
            setattr(item, "understanding", understanding)
        except Exception:
            pass


def _signal_lines(title: str, values: list[str], empty: str | None = None) -> list[str]:
    lines = [f"### {title}"]
    if not values:
        return [*lines, empty or "- None detected."]
    return [*lines, *[f"- {value}" for value in values[:8]]]


def _reproducibility_score(item: dict, understanding: PaperUnderstanding | None = None) -> float:
    score = 2.0
    if item["source"] == "github":
        score += 4.0
        if item.get("stars"):
            score += min(2.0, math.log10(item["stars"] + 1))
        if item.get("language"):
            score += 1.0
    else:
        if "github" in (item.get("summary") or "").lower() or "code" in (item.get("summary") or "").lower():
            score += 2.0
        if item["source"] == "nasa":
            score += 1.0
    if understanding is not None:
        if understanding.code_mentions:
            score += 1.5
        if understanding.dataset_mentions or understanding.metric_mentions:
            score += 1.0
    return min(10.0, score)

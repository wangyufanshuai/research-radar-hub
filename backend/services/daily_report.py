from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy.orm import Session

from backend.models.daily_report import DailyReport
from backend.repositories.cve_repo import CVERepository
from backend.repositories.daily_report_repo import DailyReportRepository
from backend.repositories.notice_repo import NoticeRepository
from backend.repositories.paper_repo import PaperRepository
from backend.repositories.repo_repo import RepoRepository
from backend.repositories.watched_page_repo import PageSnapshotRepository
from backend.services.research_radar import build_research_report_markdown


def generate_daily_report(db: Session, report_date: date | None = None, kind: str = "all") -> DailyReport:
    target_date = report_date or date.today()
    start = datetime.combine(target_date, time.min)
    end = datetime.combine(target_date, time.max)
    title = (
        f"Research Radar Daily - {target_date.isoformat()}"
        if kind == "research"
        else f"Open Data Hub {kind} Daily Report - {target_date.isoformat()}"
    )
    body = _build_markdown(db, start, end, kind)
    repo = DailyReportRepository(db)
    data = {
        "report_date": target_date,
        "kind": kind,
        "title": title,
        "body_markdown": body,
        "created_at_report": datetime.utcnow(),
    }
    existing = repo.get_by_date_kind(target_date, kind)
    if existing is None:
        report = DailyReport(**data)
        db.add(report)
        db.flush()
    else:
        for key, value in data.items():
            setattr(existing, key, value)
        report = existing
        db.flush()
    db.commit()
    return report


def _build_markdown(db: Session, start: datetime, end: datetime, kind: str) -> str:
    if kind == "research":
        return build_research_report_markdown(db, start.date(), analyze=True, use_llm=True)

    sections: list[str] = []

    if kind in {"all", "school"}:
        notices = NoticeRepository(db).search(date_from=start, date_to=end, limit=10)
        sections.append(_section("学校公告", [f"- [{n.title}]({n.url})" for n in notices]))

    if kind in {"all", "arxiv"}:
        papers = PaperRepository(db).search(date_from=start, date_to=end, limit=10)
        sections.append(_section("arXiv 论文", [f"- [{p.title}]({p.entry_url or p.pdf_url or ''})" for p in papers]))

    if kind in {"all", "github"}:
        repos = RepoRepository(db).search(date_from=start, date_to=end, limit=10)
        sections.append(_section("GitHub 项目", [f"- [{r.full_name}]({r.html_url or ''}) stars={r.stars}" for r in repos]))

    if kind in {"all", "website"}:
        snapshots = PageSnapshotRepository(db).latest_changes(limit=10)
        snapshots = [s for s in snapshots if start <= s.fetched_at <= end]
        sections.append(_section("网站变更", [f"- {s.title or s.content_hash}: {s.diff_summary or 'changed'}" for s in snapshots]))

    if kind in {"all", "cve"}:
        cves = CVERepository(db).search(date_from=start, date_to=end, limit=10)
        sections.append(_section("CVE 漏洞情报", [f"- {c.cve_id} {c.severity or ''} {c.title}" for c in cves]))

    return "\n\n".join(sections)


def _section(title: str, lines: list[str]) -> str:
    if not lines:
        lines = ["- No new items."]
    return f"## {title}\n" + "\n".join(lines)

from __future__ import annotations

from datetime import datetime
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# --- Paper ---


class PaperResponse(BaseModel):
    id: int
    arxiv_id: str
    title: str
    abstract: str | None = None
    authors: str | None = None
    categories: str | None = None
    primary_category: str | None = None
    published: datetime
    updated: datetime | None = None
    doi: str | None = None
    pdf_url: str | None = None
    entry_url: str | None = None

    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    items: list[PaperResponse]
    total: int
    offset: int
    limit: int


class PaperUnderstandingResponse(BaseModel):
    id: int
    paper_id: int | None = None
    source: str
    source_id: str
    title: str
    url: str | None = None
    pdf_url: str | None = None
    text_excerpt: str | None = None
    formula_candidates: str | None = None
    dataset_mentions: str | None = None
    code_mentions: str | None = None
    citation_mentions: str | None = None
    metric_mentions: str | None = None
    understanding_status: str
    error_message: str | None = None
    analyzed_at: datetime

    class Config:
        from_attributes = True


# --- Repo ---


class RepoResponse(BaseModel):
    id: int
    github_id: int
    full_name: str
    description: str | None = None
    language: str | None = None
    stars: int
    forks: int
    open_issues: int
    topics: str | None = None
    license_name: str | None = None
    html_url: str | None = None
    pushed_at_gh: datetime | None = None

    class Config:
        from_attributes = True


class RepoListResponse(BaseModel):
    items: list[RepoResponse]
    total: int
    offset: int
    limit: int


# --- Story ---


class StoryResponse(BaseModel):
    id: int
    hn_id: int
    item_type: str
    title: str
    url: str | None = None
    score: int
    author: str | None = None
    descendants: int
    time_published: datetime

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    items: list[StoryResponse]
    total: int
    offset: int
    limit: int


# --- Collect ---


class CollectResponse(BaseModel):
    source: str
    status: str
    records_fetched: int
    records_new: int
    records_updated: int
    duration_secs: float
    error: str | None = None


# --- Radar ---


class NoticeResponse(BaseModel):
    id: int
    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    content_hash: str
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class NoticeListResponse(BaseModel):
    items: list[NoticeResponse]
    total: int
    offset: int
    limit: int


class PageSnapshotResponse(BaseModel):
    id: int
    watched_page_id: int
    content_hash: str
    title: str | None = None
    text_excerpt: str | None = None
    diff_summary: str | None = None
    fetched_at: datetime
    status_code: int | None = None

    class Config:
        from_attributes = True


class PageSnapshotListResponse(BaseModel):
    items: list[PageSnapshotResponse]
    total: int
    offset: int
    limit: int


class CVEResponse(BaseModel):
    id: int
    cve_id: str
    source: str
    title: str
    description: str | None = None
    severity: str | None = None
    cvss_score: float | None = None
    published_at: datetime | None = None
    modified_at: datetime | None = None
    references_json: str | None = None
    affected_json: str | None = None
    content_hash: str
    first_seen_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class CVEListResponse(BaseModel):
    items: list[CVEResponse]
    total: int
    offset: int
    limit: int


class CourseItemResponse(BaseModel):
    id: int
    institution: str
    source_id: str
    title: str
    url: str
    summary: str | None = None
    department: str | None = None
    level: str | None = None
    topics: str | None = None
    published_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    content_hash: str

    class Config:
        from_attributes = True


class CourseItemListResponse(BaseModel):
    items: list[CourseItemResponse]
    total: int
    offset: int
    limit: int


class DailyReportResponse(BaseModel):
    id: int
    report_date: date
    kind: str
    title: str
    body_markdown: str
    created_at_report: datetime

    class Config:
        from_attributes = True


class EmailReportResponse(BaseModel):
    id: int
    daily_report_id: int
    subject: str
    recipient: str
    status: str
    error_message: str | None = None
    output_path: str | None = None
    sent_at: datetime | None = None
    created_at_email: datetime

    class Config:
        from_attributes = True


# --- AI Scientist ---


class ScientistTaskCreate(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    max_papers: int = Field(20, ge=1, le=50)
    max_repos: int = Field(10, ge=1, le=30)
    use_llm: bool = True


class ScientistTaskResponse(BaseModel):
    id: int
    topic: str
    status: str
    query: str | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScientistTaskItemResponse(BaseModel):
    id: int
    task_id: int
    source: str
    source_id: str
    title: str
    url: str | None = None
    summary: str | None = None
    relevance_score: float
    novelty_score: float
    reproducibility_score: float
    selected: bool
    understanding: PaperUnderstandingResponse | None = None

    class Config:
        from_attributes = True


class ScientistArtifactResponse(BaseModel):
    id: int
    task_id: int
    kind: str
    title: str
    body_markdown: str
    html_path: str | None = None
    created_at_artifact: datetime

    class Config:
        from_attributes = True


class ScientistRunResponse(BaseModel):
    id: int
    task_id: int
    stage: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    message: str | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True


class ScientistTaskDetailResponse(ScientistTaskResponse):
    items: list[ScientistTaskItemResponse] = []
    artifacts: list[ScientistArtifactResponse] = []
    runs: list[ScientistRunResponse] = []


class ScientistTaskListResponse(BaseModel):
    items: list[ScientistTaskResponse]
    total: int
    offset: int
    limit: int


# --- Analysis ---


class TrendingItem(BaseModel):
    keyword: str
    count: int


class TrendingResponse(BaseModel):
    items: list[TrendingItem]
    period_days: int


class SourceStatsResponse(BaseModel):
    total_papers: int
    total_repos: int
    total_stories: int
    papers_last_7d: int
    repos_last_7d: int
    stories_last_7d: int
    top_paper_categories: list[list]  # [category, count]
    top_repo_languages: list[list]  # [language, count]
    avg_story_score: float


# --- Health ---


class HealthResponse(BaseModel):
    status: str
    database: str

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.analysis.stats import compute_source_stats
from backend.analysis.trending import compute_trending_topics
from backend.api.deps import get_db
from backend.api.schemas import SourceStatsResponse, TrendingResponse

router = APIRouter(tags=["analysis"])


@router.get("/api/v1/analysis/stats", response_model=SourceStatsResponse)
async def get_stats(db: Session = Depends(get_db)) -> SourceStatsResponse:
    stats = compute_source_stats(db)
    return SourceStatsResponse(
        total_papers=stats.total_papers,
        total_repos=stats.total_repos,
        total_stories=stats.total_stories,
        papers_last_7d=stats.papers_last_7d,
        repos_last_7d=stats.repos_last_7d,
        stories_last_7d=stats.stories_last_7d,
        top_paper_categories=stats.top_paper_categories,
        top_repo_languages=stats.top_repo_languages,
        avg_story_score=stats.avg_story_score,
    )


@router.get("/api/v1/analysis/trending", response_model=TrendingResponse)
async def get_trending(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
) -> TrendingResponse:
    items = compute_trending_topics(db, days=days)
    return TrendingResponse(
        items=items,
        period_days=days,
    )

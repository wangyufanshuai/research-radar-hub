from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import RepoListResponse, RepoResponse
from backend.repositories.repo_repo import RepoRepository

router = APIRouter(tags=["repos"])


@router.get("/api/v1/repos", response_model=RepoListResponse)
async def list_repos(
    keyword: str | None = Query(None),
    language: str | None = Query(None),
    min_stars: int | None = Query(None, ge=0),
    max_stars: int | None = Query(None, ge=0),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> RepoListResponse:
    repo = RepoRepository(db)
    repos = repo.search(
        keyword=keyword,
        language=language,
        min_stars=min_stars,
        max_stars=max_stars,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    total = repo.search_count(
        keyword=keyword,
        language=language,
        min_stars=min_stars,
        max_stars=max_stars,
        date_from=date_from,
        date_to=date_to,
    )
    return RepoListResponse(
        items=[RepoResponse.model_validate(r) for r in repos],
        total=total,
        offset=offset,
        limit=limit,
    )

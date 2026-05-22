from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import StoryListResponse, StoryResponse
from backend.repositories.story_repo import StoryRepository

router = APIRouter(tags=["stories"])


@router.get("/api/v1/stories", response_model=StoryListResponse)
async def list_stories(
    keyword: str | None = Query(None),
    min_score: int | None = Query(None, ge=0),
    max_score: int | None = Query(None, ge=0),
    item_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> StoryListResponse:
    repo = StoryRepository(db)
    stories = repo.search(
        keyword=keyword,
        min_score=min_score,
        max_score=max_score,
        item_type=item_type,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    total = repo.search_count(
        keyword=keyword,
        min_score=min_score,
        max_score=max_score,
        item_type=item_type,
        date_from=date_from,
        date_to=date_to,
    )
    return StoryListResponse(
        items=[StoryResponse.model_validate(s) for s in stories],
        total=total,
        offset=offset,
        limit=limit,
    )

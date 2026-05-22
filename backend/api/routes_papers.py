from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import PaperListResponse, PaperResponse
from backend.repositories.paper_repo import PaperRepository

router = APIRouter(tags=["papers"])


@router.get("/api/v1/papers", response_model=PaperListResponse)
async def list_papers(
    keyword: str | None = Query(None),
    category: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaperListResponse:
    repo = PaperRepository(db)
    papers = repo.search(
        keyword=keyword,
        category=category,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    total = repo.search_count(
        keyword=keyword,
        category=category,
        date_from=date_from,
        date_to=date_to,
    )
    return PaperListResponse(
        items=[PaperResponse.model_validate(p) for p in papers],
        total=total,
        offset=offset,
        limit=limit,
    )

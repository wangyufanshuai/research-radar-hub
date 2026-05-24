from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import (
    ScientistArtifactResponse,
    ScientistTaskCreate,
    ScientistTaskDetailResponse,
    ScientistTaskListResponse,
    ScientistTaskResponse,
)
from backend.repositories.scientist_repo import ScientistTaskRepository
from backend.repositories.paper_understanding_repo import PaperUnderstandingRepository
from backend.services.ai_scientist import create_scientist_task, run_scientist_task

router = APIRouter(prefix="/api/v1/scientist", tags=["ai-scientist"])


@router.post("/tasks", response_model=ScientistTaskResponse)
async def create_task(payload: ScientistTaskCreate, db: Session = Depends(get_db)) -> ScientistTaskResponse:
    task = create_scientist_task(db, payload.topic)
    return ScientistTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/run", response_model=ScientistTaskDetailResponse)
async def run_task(
    task_id: int,
    max_papers: int = Query(20, ge=1, le=50),
    max_repos: int = Query(10, ge=1, le=30),
    use_llm: bool = Query(True),
    db: Session = Depends(get_db),
) -> ScientistTaskDetailResponse:
    try:
        task = run_scientist_task(db, task_id, max_papers=max_papers, max_repos=max_repos, use_llm=use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _attach_understandings(db, task)
    return ScientistTaskDetailResponse.model_validate(task)


@router.get("/tasks", response_model=ScientistTaskListResponse)
async def list_tasks(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ScientistTaskListResponse:
    repo = ScientistTaskRepository(db)
    return ScientistTaskListResponse(
        items=[ScientistTaskResponse.model_validate(task) for task in repo.list_recent(offset=offset, limit=limit)],
        total=repo.count(),
        offset=offset,
        limit=limit,
    )


@router.get("/tasks/{task_id}", response_model=ScientistTaskDetailResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)) -> ScientistTaskDetailResponse:
    task = ScientistTaskRepository(db).get_detail(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Scientist task not found: {task_id}")
    _attach_understandings(db, task)
    return ScientistTaskDetailResponse.model_validate(task)


@router.get("/tasks/{task_id}/report", response_model=ScientistArtifactResponse)
async def get_task_report(task_id: int, db: Session = Depends(get_db)) -> ScientistArtifactResponse:
    task = ScientistTaskRepository(db).get_detail(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Scientist task not found: {task_id}")
    reports = [artifact for artifact in task.artifacts if artifact.kind == "report"]
    if not reports:
        raise HTTPException(status_code=404, detail=f"Report not found for task: {task_id}")
    reports.sort(key=lambda artifact: artifact.created_at_artifact, reverse=True)
    return ScientistArtifactResponse.model_validate(reports[0])


def _attach_understandings(db: Session, task) -> None:
    repo = PaperUnderstandingRepository(db)
    for item in task.items:
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

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_analysis import router as analysis_router
from backend.api.routes_collect import router as collect_router
from backend.api.routes_health import router as health_router
from backend.api.routes_papers import router as papers_router
from backend.api.routes_radar import router as radar_router
from backend.api.routes_reports import router as reports_router
from backend.api.routes_repos import router as repos_router
from backend.api.routes_scientist import router as scientist_router
from backend.api.routes_stories import router as stories_router
from backend.core.config import get_config
from backend.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Research Radar Hub",
    version="0.5.0",
    description="Local-first research intelligence, AI Scientist, and paper understanding API.",
    lifespan=lifespan,
)

config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers_router)
app.include_router(repos_router)
app.include_router(stories_router)
app.include_router(collect_router)
app.include_router(radar_router)
app.include_router(reports_router)
app.include_router(analysis_router)
app.include_router(scientist_router)
app.include_router(health_router)

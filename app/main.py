"""PepperFlow AI — Agentic Workflow Automation Platform."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.workflows import router as workflows_router
from app.api.agents import router as agents_router
from app.api.audit import router as audit_router
from app.core.config import settings
from app.core.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="PepperFlow AI",
    description="Agentic Workflow Automation Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows_router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["audit"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pepperflow-ai"}

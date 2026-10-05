import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.database import AsyncSessionLocal, create_db_and_tables
from backend.routes import auth_routes, upload_routes, analysis_routes, assignment_routes
from backend.utils.load_sources import load_academic_sources
from backend.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ---------------------------------------------------------------------------
# Lifespan — create tables + seed academic sources
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # create_db_and_tables() is fully async — no sync/asyncio conflict.
        # For schema changes in production, run: docker-compose exec backend alembic upgrade head
        await create_db_and_tables()
        logger.info("db.tables_ready")
        logger.info("startup.config", embedding_model=EMBEDDING_MODEL, n8n_url=N8N_WEBHOOK_URL)

        async with AsyncSessionLocal() as db:
            await load_academic_sources(db)

    except Exception as e:
        logger.error("startup.failed", error=str(e))

    yield

    logger.info("shutdown.complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Academic Assignment Helper & Plagiarism Detector",
    description=(
        "RAG-powered API for uploading student assignments, detecting plagiarism via "
        "pgvector semantic search, and generating AI-driven research suggestions."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(upload_routes.router)
app.include_router(assignment_routes.router)
app.include_router(analysis_routes.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Academic Assignment Helper is running 🚀"}

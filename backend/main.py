import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.database import create_db_and_tables, AsyncSessionLocal
from backend.routes import auth_routes, upload_routes, analysis_routes, assignment_routes
from backend.utils.load_sources import load_academic_sources

# Environment variables
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables and seed academic sources."""
    try:
        await create_db_and_tables()
        print("✅ Database tables created and connected successfully")
        print(f"🔗 Using Embedding Model: {EMBEDDING_MODEL}")
        print(f"🌐 N8N Webhook URL: {N8N_WEBHOOK_URL}")

        # AsyncSessionLocal() is a proper async context manager — use it directly
        # (get_db() is an async generator meant for FastAPI Depends, not for use here)
        async with AsyncSessionLocal() as db:
            await load_academic_sources(db)

    except Exception as e:
        print("❌ Error during startup:", e)

    yield  # application runs here

    # Shutdown cleanup (extend as needed)
    print("🛑 Application shutting down.")


app = FastAPI(
    title="Academic Assignment Helper & Plagiarism Detector",
    description="RAG-Powered API for assignment uploads and AI analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Routers
app.include_router(auth_routes.router)
app.include_router(upload_routes.router)
app.include_router(assignment_routes.router)
app.include_router(analysis_routes.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Academic Assignment Helper Backend is running 🚀"}

import asyncio
import os
from fastapi import FastAPI
from backend.database import create_db_and_tables, get_db
from backend.routes import auth_routes, upload_routes, analysis_routes
from backend.utils.load_sources import load_academic_sources  # ✅ New import

# Environment variables (for embedding + n8n)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

app = FastAPI(
    title="Academic Assignment Helper & Plagiarism Detector",
    description="RAG-Powered API for assignment uploads and AI analysis",
    version="1.0.0"
)

# Routers
app.include_router(auth_routes.router)
app.include_router(upload_routes.router)
app.include_router(analysis_routes.router)

@app.on_event("startup")
async def on_startup():
    """Create DB tables, ensure pgvector is ready, and load academic sources."""
    try:
        await create_db_and_tables()
        print("✅ Database tables created and connected successfully")
        print(f"🔗 Using Embedding Model: {EMBEDDING_MODEL}")
        print(f"🌐 N8N Webhook URL: {N8N_WEBHOOK_URL}")

        # ✅ Load academic sources once when backend starts
        async with get_db() as db:
            await load_academic_sources(db)

    except Exception as e:
        print("❌ Error during startup:", e)

@app.get("/")
def root():
    return {"message": "Academic Assignment Helper Backend is running 🚀"}

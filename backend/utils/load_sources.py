import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AcademicSource
from backend.rag_service import get_embedding

async def load_academic_sources(db: AsyncSession, path="backend/data/academic_sources.json"):
    if not os.path.exists(path):
        print(f"⚠️ No academic sources file found at {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # Only load if database is empty
    existing = await db.execute("SELECT COUNT(*) FROM academic_sources")
    count = existing.scalar()
    if count and count > 0:
        print("✅ Academic sources already loaded.")
        return

    retry_info = {"count": 0}
    for s in sources:
        try:
            embedding = await get_embedding(s["abstract"], retry_info)
            db.add(AcademicSource(**s, embedding=embedding))
        except Exception as e:
            print(f"⚠️ Failed to embed {s['title']}: {e}")

    await db.commit()
    print(f"✅ Loaded {len(sources)} academic sources into database.")

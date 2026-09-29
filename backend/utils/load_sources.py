import json
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AcademicSource
from backend.rag_service import get_embedding

# The sample data lives at data/sample_academic_sources.json (mounted to /app/data in Docker)
DEFAULT_SOURCES_PATH = os.path.join(
    os.path.dirname(__file__),  # backend/utils/
    "..", "..",                  # -> project root
    "data", "sample_academic_sources.json"
)


async def load_academic_sources(db: AsyncSession, path: str = DEFAULT_SOURCES_PATH):
    """Seed the academic_sources table from a JSON file if it is empty."""
    resolved = os.path.abspath(path)
    if not os.path.exists(resolved):
        print(f"⚠️  No academic sources file found at {resolved}")
        return

    with open(resolved, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # SQLAlchemy 2.x requires text() for raw SQL strings
    result = await db.execute(text("SELECT COUNT(*) FROM academic_sources"))
    count = result.scalar()
    if count and count > 0:
        print(f"✅ Academic sources already loaded ({count} records). Skipping seed.")
        return

    loaded = 0
    for s in sources:
        abstract = s.get("abstract", "")
        if not abstract:
            print(f"⚠️  Skipping '{s.get('title')}' — no abstract to embed.")
            continue
        try:
            # get_embedding() takes a single text argument
            embedding = await get_embedding(abstract)
            db.add(AcademicSource(
                title=s.get("title"),
                authors=s.get("authors"),
                publication_year=s.get("publication_year"),
                abstract=abstract,
                full_text=s.get("full_text"),
                source_type=s.get("source_type"),
                embedding=embedding,
            ))
            loaded += 1
        except Exception as e:
            print(f"⚠️  Failed to embed '{s.get('title')}': {e}")

    await db.commit()
    print(f"✅ Loaded {loaded}/{len(sources)} academic sources into database.")

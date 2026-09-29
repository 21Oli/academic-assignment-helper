import json
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AcademicSource
from backend.rag_service import get_embedding
from backend.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SOURCES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_academic_sources.json")
)


async def load_academic_sources(db: AsyncSession, path: str = DEFAULT_SOURCES_PATH):
    """Seed the academic_sources table from a JSON file if it is empty."""
    resolved = os.path.abspath(path)
    if not os.path.exists(resolved):
        logger.warning("load_sources.file_not_found", path=resolved)
        return

    with open(resolved, "r", encoding="utf-8") as f:
        sources = json.load(f)

    result = await db.execute(text("SELECT COUNT(*) FROM academic_sources"))
    count = result.scalar()
    if count and count > 0:
        logger.info("load_sources.already_seeded", count=count)
        return

    loaded = 0
    for s in sources:
        abstract = s.get("abstract", "")
        if not abstract:
            logger.warning("load_sources.skip_no_abstract", title=s.get("title"))
            continue
        try:
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
            logger.warning("load_sources.embed_failed", title=s.get("title"), error=str(e))

    await db.commit()
    logger.info("load_sources.complete", loaded=loaded, total=len(sources))

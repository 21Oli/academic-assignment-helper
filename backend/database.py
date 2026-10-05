import os
import ssl
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


def _build_engine_args(raw_url: str) -> tuple[str, dict]:
    """
    asyncpg does not support SSL-related query params (sslmode, ssl,
    channel_binding, etc.) in the connection URL — they must be passed
    via connect_args.

    This function:
    1. Strips ALL query params from the URL
    2. Returns a clean URL + connect_args with SSL configured if the
       original URL contained any SSL-related params.
    """
    parsed = urlparse(raw_url)
    params = parse_qs(parsed.query)

    # Detect whether SSL is required
    needs_ssl = (
        params.get("sslmode", [""])[0] in ("require", "verify-ca", "verify-full")
        or params.get("ssl", [""])[0] in ("true", "1", "require")
    )

    # Remove ALL query params — asyncpg doesn't handle any of them
    clean = parsed._replace(query="")
    clean_url = urlunparse(clean)

    connect_args: dict = {}
    if needs_ssl:
        ctx = ssl.create_default_context()
        connect_args["ssl"] = ctx

    return clean_url, connect_args


_clean_url, _connect_args = _build_engine_args(DATABASE_URL)

engine = create_async_engine(
    _clean_url,
    future=True,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_db_and_tables():
    from sqlalchemy import text
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
        await conn.run_sync(Base.metadata.create_all)

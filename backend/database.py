import os
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

# asyncpg does not accept ?sslmode=require in the URL — strip it out and
# pass SSL via connect_args instead. This handles both Neon (production)
# and local Docker Postgres (no SSL needed).
_url = DATABASE_URL
_connect_args: dict = {}

if "sslmode=require" in _url:
    # Remove the query param and configure SSL properly for asyncpg
    _url = _url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    _ssl_ctx = ssl.create_default_context()
    _connect_args["ssl"] = _ssl_ctx
elif "ssl=true" in _url:
    _url = _url.replace("?ssl=true", "").replace("&ssl=true", "")
    _ssl_ctx = ssl.create_default_context()
    _connect_args["ssl"] = _ssl_ctx

engine = create_async_engine(
    _url,
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

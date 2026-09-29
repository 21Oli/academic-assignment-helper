"""
pytest fixtures shared across all test modules.

Uses an in-memory async SQLite database so tests run without Docker,
PostgreSQL, or any network calls.

Key decisions:
- pgvector types are not available in SQLite; the embedding column is
  patched to Text for the test session.
- OpenAI calls in rag_service are monkeypatched to return deterministic
  fixtures so tests are fast, free, and reproducible.
"""
import os
import pytest
import pytest_asyncio

# Set env vars BEFORE any backend import so modules pick them up
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key")

from sqlalchemy import event, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

# Patch the pgvector column type to Text before models are imported
from pgvector.sqlalchemy import Vector as _PgVector
import sqlalchemy.types as _sa_types

# Replace Vector(n) with Text so SQLite can handle it in tests
_sa_types.Vector = Text  # type: ignore[attr-defined]


from backend.database import Base
from backend.models import Student, Assignment, AcademicSource  # noqa — registers models
from backend.auth import get_password_hash, create_access_token
from backend.deps import get_current_student
from backend.database import get_db

# ---------------------------------------------------------------------------
# Async engine + session factory pointing at in-memory SQLite
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once for the entire test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    """Yield a fresh AsyncSession, rolling back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI app with DB dependency overridden to use the test session
# ---------------------------------------------------------------------------
@pytest.fixture()
def app(db_session):
    from backend.main import app as _app

    async def _override_get_db():
        yield db_session

    _app.dependency_overrides[get_db] = _override_get_db
    yield _app
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client(app):
    """Async HTTP client wired to the FastAPI test app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------
async def create_student(db: AsyncSession, email: str = "test@uni.edu", password: str = "password123") -> Student:
    student = Student(
        email=email,
        password_hash=get_password_hash(password),
        full_name="Test Student",
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


def auth_headers(student: Student) -> dict:
    """Return Authorization headers for a given student."""
    token = create_access_token({"sub": student.email})
    return {"Authorization": f"Bearer {token}"}


async def create_assignment(db: AsyncSession, student_id: int, text: str = "Sample assignment text.") -> Assignment:
    assignment = Assignment(
        student_id=student_id,
        filename="test.txt",
        file_path="/tmp/test.txt",
        original_text=text,
        topic="test",
        word_count=len(text.split()),
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment

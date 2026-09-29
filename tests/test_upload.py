"""Tests for POST /upload/ — file upload endpoint."""
import io
import pytest
from tests.conftest import create_student, auth_headers


@pytest.mark.asyncio
async def test_upload_txt_success(client, db_session):
    student = await create_student(db_session, email="uploader@uni.edu")

    file_content = b"This is a test assignment about artificial intelligence and machine learning."
    resp = await client.post(
        "/upload/",
        files={"file": ("assignment.txt", io.BytesIO(file_content), "text/plain")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["assignment_id"], int)


@pytest.mark.asyncio
async def test_upload_requires_auth(client):
    file_content = b"Some text"
    resp = await client.post(
        "/upload/",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_too_large(client, db_session):
    student = await create_student(db_session, email="bigfile@uni.edu")

    # 21 MB of data — exceeds the 20 MB limit
    big_content = b"x" * (21 * 1024 * 1024)
    resp = await client.post(
        "/upload/",
        files={"file": ("big.txt", io.BytesIO(big_content), "text/plain")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_returns_word_count(client, db_session):
    """Word count should be stored on the assignment record."""
    from sqlalchemy import select
    from backend.models import Assignment

    student = await create_student(db_session, email="wordcount@uni.edu")
    text = b"word " * 100  # 100 words

    resp = await client.post(
        "/upload/",
        files={"file": ("essay.txt", io.BytesIO(text), "text/plain")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    aid = resp.json()["assignment_id"]

    res = await db_session.execute(select(Assignment).filter(Assignment.id == aid))
    assignment = res.scalars().first()
    assert assignment is not None
    assert assignment.word_count == 100

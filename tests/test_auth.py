"""Tests for POST /auth/register, POST /auth/login, GET /auth/me."""
import pytest
from tests.conftest import create_student, auth_headers


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "email": "newuser@uni.edu",
        "password": "securepass1",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["message"] == "User registered successfully"
    assert isinstance(body["user_id"], int)


@pytest.mark.asyncio
async def test_register_duplicate_email(client, db_session):
    await create_student(db_session, email="dup@uni.edu")

    resp = await client.post("/auth/register", json={
        "email": "dup@uni.edu",
        "password": "securepass1",
        "full_name": "Duplicate",
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_short_password(client):
    resp = await client.post("/auth/register", json={
        "email": "short@uni.edu",
        "password": "abc",       # < 8 chars
        "full_name": "Short",
    })
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_login_success(client, db_session):
    await create_student(db_session, email="login@uni.edu", password="mypassword1")

    resp = await client.post("/auth/login", json={
        "email": "login@uni.edu",
        "password": "mypassword1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, db_session):
    await create_student(db_session, email="wrong@uni.edu", password="correctpass1")

    resp = await client.post("/auth/login", json={
        "email": "wrong@uni.edu",
        "password": "wrongpass123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    resp = await client.post("/auth/login", json={
        "email": "nobody@uni.edu",
        "password": "doesntmatter",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client, db_session):
    student = await create_student(db_session, email="me@uni.edu")
    resp = await client.get("/auth/me", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@uni.edu"
    assert body["full_name"] == "Test Student"
    assert "id" in body


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403

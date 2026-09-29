"""Tests for GET /assignments/, GET /assignments/{id}, DELETE /assignments/{id}."""
import pytest
from tests.conftest import create_student, create_assignment, auth_headers


@pytest.mark.asyncio
async def test_list_assignments_empty(client, db_session):
    student = await create_student(db_session, email="list_empty@uni.edu")
    resp = await client.get("/assignments/", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_assignments_returns_own_only(client, db_session):
    student_a = await create_student(db_session, email="owner_a@uni.edu")
    student_b = await create_student(db_session, email="owner_b@uni.edu")

    # student_a has 2 assignments, student_b has 1
    await create_assignment(db_session, student_a.id, "Assignment one")
    await create_assignment(db_session, student_a.id, "Assignment two")
    await create_assignment(db_session, student_b.id, "Other student assignment")

    resp = await client.get("/assignments/", headers=auth_headers(student_a))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_assignments_pagination(client, db_session):
    student = await create_student(db_session, email="paginate@uni.edu")
    for i in range(5):
        await create_assignment(db_session, student.id, f"Assignment {i}")

    resp = await client.get("/assignments/?page=1&page_size=2", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_get_assignment_detail(client, db_session):
    student = await create_student(db_session, email="detail@uni.edu")
    assignment = await create_assignment(db_session, student.id, "Detail test text")

    resp = await client.get(f"/assignments/{assignment.id}", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == assignment.id
    assert body["has_analysis"] is False
    assert body["latest_analysis"] is None


@pytest.mark.asyncio
async def test_get_assignment_not_found(client, db_session):
    student = await create_student(db_session, email="notfound@uni.edu")
    resp = await client.get("/assignments/99999", headers=auth_headers(student))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_assignment_other_student_forbidden(client, db_session):
    """A student cannot access another student's assignment."""
    owner = await create_student(db_session, email="owner@uni.edu")
    intruder = await create_student(db_session, email="intruder@uni.edu")
    assignment = await create_assignment(db_session, owner.id, "Private assignment")

    resp = await client.get(f"/assignments/{assignment.id}", headers=auth_headers(intruder))
    assert resp.status_code == 404  # treated as not-found, not 403, to avoid enumeration


@pytest.mark.asyncio
async def test_delete_assignment(client, db_session):
    student = await create_student(db_session, email="delete@uni.edu")
    assignment = await create_assignment(db_session, student.id, "To be deleted")

    resp = await client.delete(f"/assignments/{assignment.id}", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify it's gone
    resp2 = await client.get(f"/assignments/{assignment.id}", headers=auth_headers(student))
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_assignment_other_student_forbidden(client, db_session):
    owner = await create_student(db_session, email="del_owner@uni.edu")
    intruder = await create_student(db_session, email="del_intruder@uni.edu")
    assignment = await create_assignment(db_session, owner.id, "Owner's work")

    resp = await client.delete(f"/assignments/{assignment.id}", headers=auth_headers(intruder))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_assignments_requires_auth(client):
    resp = await client.get("/assignments/")
    assert resp.status_code == 403

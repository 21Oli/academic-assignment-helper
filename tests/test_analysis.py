"""
Tests for POST /analysis/start and GET /analysis/{id}.

OpenAI calls are monkeypatched so tests run without API keys or network.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import create_student, create_assignment, auth_headers
from backend.models import AnalysisResult, AcademicSource


# ---------------------------------------------------------------------------
# Helpers — fake embedding and fake LLM response
# ---------------------------------------------------------------------------
FAKE_EMBEDDING = [0.01] * 1536  # valid 1536-dim vector

FAKE_LLM_RESPONSE = json.dumps({
    "topic": "Artificial Intelligence",
    "key_themes": ["deep learning", "NLP"],
    "research_questions": ["How does AI affect education?"],
    "academic_level": "undergraduate",
    "research_suggestions": "Consider exploring transformer architectures.",
    "citation_recommendations": "Cite LeCun et al. 2021.",
    "confidence_score": 0.82,
})


async def _fake_get_embedding(text_input: str):
    return FAKE_EMBEDDING


async def _fake_call_chat_completion(system_prompt: str, user_prompt: str):
    return FAKE_LLM_RESPONSE


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_start_analysis_single(client, db_session):
    student = await create_student(db_session, email="analysis1@uni.edu")
    assignment = await create_assignment(
        db_session, student.id,
        "Artificial intelligence is transforming how we approach complex problems."
    )

    with patch("backend.rag_service.get_embedding", side_effect=_fake_get_embedding), \
         patch("backend.rag_service.call_chat_completion", side_effect=_fake_call_chat_completion):

        resp = await client.post(
            "/analysis/start",
            json={"assignment_id": assignment.id},
            headers=auth_headers(student),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert "analysis_id" in body["result"]
    assert isinstance(body["result"]["plagiarism_score"], float)


@pytest.mark.asyncio
async def test_start_analysis_batch(client, db_session):
    student = await create_student(db_session, email="batch@uni.edu")
    a1 = await create_assignment(db_session, student.id, "Assignment about machine learning.")
    a2 = await create_assignment(db_session, student.id, "Assignment about blockchain.")

    with patch("backend.rag_service.get_embedding", side_effect=_fake_get_embedding), \
         patch("backend.rag_service.call_chat_completion", side_effect=_fake_call_chat_completion):

        resp = await client.post(
            "/analysis/start",
            json={"assignment_ids": [a1.id, a2.id]},
            headers=auth_headers(student),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert len(body["results"]) == 2
    for item in body["results"]:
        assert "result" in item or "error" in item


@pytest.mark.asyncio
async def test_start_analysis_wrong_owner(client, db_session):
    owner = await create_student(db_session, email="an_owner@uni.edu")
    attacker = await create_student(db_session, email="an_attacker@uni.edu")
    assignment = await create_assignment(db_session, owner.id, "Private work.")

    resp = await client.post(
        "/analysis/start",
        json={"assignment_id": assignment.id},
        headers=auth_headers(attacker),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_analysis_no_payload(client, db_session):
    student = await create_student(db_session, email="nopayload@uni.edu")
    resp = await client.post(
        "/analysis/start",
        json={},
        headers=auth_headers(student),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_analysis_result(client, db_session):
    student = await create_student(db_session, email="getresult@uni.edu")
    assignment = await create_assignment(db_session, student.id, "Test text for result.")

    # Manually insert an AnalysisResult
    result = AnalysisResult(
        assignment_id=assignment.id,
        suggested_sources=[],
        plagiarism_score=0.12,
        flagged_sections=[],
        research_suggestions="Look into more sources.",
        citation_recommendations="Use APA style.",
        confidence_score=0.9,
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)

    resp = await client.get(f"/analysis/{assignment.id}", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plagiarism_score"] == pytest.approx(0.12)
    assert body["confidence_score"] == pytest.approx(0.9)
    assert body["research_suggestions"] == "Look into more sources."


@pytest.mark.asyncio
async def test_get_analysis_not_yet_run(client, db_session):
    student = await create_student(db_session, email="noanalysis@uni.edu")
    assignment = await create_assignment(db_session, student.id, "Text without analysis.")

    resp = await client.get(f"/analysis/{assignment.id}", headers=auth_headers(student))
    assert resp.status_code == 404
    assert "analysis/start" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_analysis_requires_auth(client, db_session):
    resp = await client.post("/analysis/start", json={"assignment_id": 1})
    assert resp.status_code == 403

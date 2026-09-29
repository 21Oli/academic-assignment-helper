"""
Pydantic request and response schemas.

Using these on every route gives us:
- Automatic input validation with clear error messages
- Proper Swagger/OpenAPI docs with example values
- Type-safe response serialisation
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72, description="8–72 characters")
    full_name: str = Field(..., min_length=1, max_length=120)

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "student@university.edu",
                "password": "securepass123",
                "full_name": "Jane Doe",
            }
        }
    }


class RegisterResponse(BaseModel):
    message: str
    user_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {"email": "student@university.edu", "password": "securepass123"}
        }
    }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StudentProfile(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

class AssignmentSummary(BaseModel):
    id: int
    filename: Optional[str]
    topic: Optional[str]
    academic_level: Optional[str]
    word_count: Optional[int]
    uploaded_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AnalysisSummary(BaseModel):
    analysis_id: int
    plagiarism_score: Optional[float]
    confidence_score: Optional[float]
    flagged_sections_count: int
    research_suggestions: Optional[str]
    citation_recommendations: Optional[str]
    analyzed_at: Optional[datetime]


class AssignmentDetail(AssignmentSummary):
    has_analysis: bool
    latest_analysis: Optional[AnalysisSummary] = None


class AssignmentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[AssignmentSummary]


class UploadResponse(BaseModel):
    success: bool
    message: str
    assignment_id: int


class DeleteResponse(BaseModel):
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class StartAnalysisRequest(BaseModel):
    assignment_id: Optional[int] = Field(None, description="Single assignment ID")
    assignment_ids: Optional[List[int]] = Field(None, description="Batch of assignment IDs")

    @field_validator("assignment_ids")
    @classmethod
    def ids_not_empty(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None and len(v) == 0:
            raise ValueError("assignment_ids must not be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"assignment_id": 1},
                {"assignment_ids": [1, 2, 3]},
            ]
        }
    }


class SourceMatch(BaseModel):
    id: int
    title: Optional[str]
    authors: Optional[str]
    publication_year: Optional[int]
    abstract: Optional[str]
    source_type: Optional[str]
    score: float


class AnalysisResultResponse(BaseModel):
    id: int
    assignment_id: int
    suggested_sources: Optional[List[Dict[str, Any]]]
    plagiarism_score: Optional[float]
    flagged_sections: Optional[List[Dict[str, Any]]]
    research_suggestions: Optional[str]
    citation_recommendations: Optional[str]
    confidence_score: Optional[float]
    analyzed_at: Optional[datetime]


class SingleAnalysisResult(BaseModel):
    analysis_id: int
    plagiarism_score: float
    flagged_sections_count: int
    top_sources: List[Dict[str, Any]]
    llm_parsed: Dict[str, Any]


class StartAnalysisSingleResponse(BaseModel):
    status: str
    result: SingleAnalysisResult


class BatchResultItem(BaseModel):
    assignment_id: int
    result: Optional[SingleAnalysisResult] = None
    error: Optional[str] = None


class StartAnalysisBatchResponse(BaseModel):
    status: str
    results: List[BatchResultItem]


# ---------------------------------------------------------------------------
# Generic error (used by exception handlers)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str

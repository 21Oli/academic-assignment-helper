# backend/routes/assignment_routes.py
import os
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models import Assignment, AnalysisResult, Student
from backend.deps import get_current_student
from backend.schemas import (
    AssignmentListResponse,
    AssignmentSummary,
    AssignmentDetail,
    AnalysisSummary,
    DeleteResponse,
)

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.get(
    "/",
    response_model=AssignmentListResponse,
    summary="List all assignments for the current student",
)
async def list_assignments(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Requires: Authorization: Bearer <token>"""
    offset = (page - 1) * page_size

    count_res = await db.execute(
        select(func.count(Assignment.id)).filter(Assignment.student_id == current_student.id)
    )
    total = count_res.scalar() or 0

    res = await db.execute(
        select(Assignment)
        .filter(Assignment.student_id == current_student.id)
        .order_by(Assignment.uploaded_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    assignments = res.scalars().all()

    return AssignmentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
        items=[AssignmentSummary.model_validate(a) for a in assignments],
    )


@router.get(
    "/{assignment_id}",
    response_model=AssignmentDetail,
    summary="Get details of a single assignment",
)
async def get_assignment(
    assignment_id: int,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full details plus the latest analysis summary if one exists.
    Requires: Authorization: Bearer <token>
    """
    res = await db.execute(
        select(Assignment).filter(
            Assignment.id == assignment_id,
            Assignment.student_id == current_student.id,
        )
    )
    assignment = res.scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    analysis_res = await db.execute(
        select(AnalysisResult)
        .filter(AnalysisResult.assignment_id == assignment_id)
        .order_by(AnalysisResult.analyzed_at.desc())
    )
    latest = analysis_res.scalars().first()

    analysis_summary = None
    if latest:
        analysis_summary = AnalysisSummary(
            analysis_id=latest.id,
            plagiarism_score=latest.plagiarism_score,
            confidence_score=latest.confidence_score,
            flagged_sections_count=len(latest.flagged_sections or []),
            research_suggestions=latest.research_suggestions,
            citation_recommendations=latest.citation_recommendations,
            analyzed_at=latest.analyzed_at,
        )

    return AssignmentDetail(
        id=assignment.id,
        filename=assignment.filename,
        topic=assignment.topic,
        academic_level=assignment.academic_level,
        word_count=assignment.word_count,
        uploaded_at=assignment.uploaded_at,
        has_analysis=latest is not None,
        latest_analysis=analysis_summary,
    )


@router.delete(
    "/{assignment_id}",
    response_model=DeleteResponse,
    summary="Delete an assignment and all its analysis results",
)
async def delete_assignment(
    assignment_id: int,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently deletes the assignment, all its analysis results, and the
    uploaded file from disk.
    Requires: Authorization: Bearer <token>
    """
    res = await db.execute(
        select(Assignment).filter(
            Assignment.id == assignment_id,
            Assignment.student_id == current_student.id,
        )
    )
    assignment = res.scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.file_path and os.path.exists(assignment.file_path):
        try:
            os.remove(assignment.file_path)
        except Exception as e:
            print(f"⚠️  Could not delete file {assignment.file_path}: {e}")

    await db.delete(assignment)
    await db.commit()

    return DeleteResponse(success=True, message=f"Assignment {assignment_id} deleted.")

# backend/routes/assignment_routes.py
import os
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models import Assignment, AnalysisResult, Student
from backend.deps import get_current_student

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.get("/", summary="List all assignments for the current student")
async def list_assignments(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of assignments belonging to the authenticated student.
    Requires:  Authorization: Bearer <token>
    """
    offset = (page - 1) * page_size

    # Total count for pagination metadata
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

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     max(1, -(-total // page_size)),  # ceiling division
        "items": [
            {
                "id":             a.id,
                "filename":       a.filename,
                "topic":          a.topic,
                "academic_level": a.academic_level,
                "word_count":     a.word_count,
                "uploaded_at":    a.uploaded_at.isoformat() if a.uploaded_at else None,
            }
            for a in assignments
        ],
    }


@router.get("/{assignment_id}", summary="Get details of a single assignment")
async def get_assignment(
    assignment_id: int,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full details of an assignment including its latest analysis summary
    (if one exists).  Only the owning student can access this.
    Requires:  Authorization: Bearer <token>
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

    # Attach latest analysis summary if available
    analysis_res = await db.execute(
        select(AnalysisResult)
        .filter(AnalysisResult.assignment_id == assignment_id)
        .order_by(AnalysisResult.analyzed_at.desc())
    )
    latest = analysis_res.scalars().first()

    analysis_summary = None
    if latest:
        analysis_summary = {
            "analysis_id":              latest.id,
            "plagiarism_score":         latest.plagiarism_score,
            "confidence_score":         latest.confidence_score,
            "flagged_sections_count":   len(latest.flagged_sections or []),
            "research_suggestions":     latest.research_suggestions,
            "citation_recommendations": latest.citation_recommendations,
            "analyzed_at":              latest.analyzed_at.isoformat() if latest.analyzed_at else None,
        }

    return {
        "id":              assignment.id,
        "filename":        assignment.filename,
        "topic":           assignment.topic,
        "academic_level":  assignment.academic_level,
        "word_count":      assignment.word_count,
        "uploaded_at":     assignment.uploaded_at.isoformat() if assignment.uploaded_at else None,
        "has_analysis":    latest is not None,
        "latest_analysis": analysis_summary,
    }


@router.delete("/{assignment_id}", summary="Delete an assignment and its analysis results")
async def delete_assignment(
    assignment_id: int,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently deletes an assignment and all its associated analysis results.
    Also removes the uploaded file from disk if it still exists.
    Only the owning student can delete their assignment.
    Requires:  Authorization: Bearer <token>
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

    # Remove the uploaded file from disk (best-effort)
    if assignment.file_path and os.path.exists(assignment.file_path):
        try:
            os.remove(assignment.file_path)
        except Exception as e:
            print(f"⚠️  Could not delete file {assignment.file_path}: {e}")

    # Cascade delete handles AnalysisResult rows (defined on the model)
    await db.delete(assignment)
    await db.commit()

    return {"success": True, "message": f"Assignment {assignment_id} deleted."}

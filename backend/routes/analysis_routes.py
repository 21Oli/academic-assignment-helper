# backend/routes/analysis_routes.py
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import Assignment, AnalysisResult, Student
from backend.rag_service import analyze_assignment_and_save
from backend.deps import get_current_student

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/start", summary="Trigger analysis for one or more assignments")
async def start_analysis(
    assignment_id: int = Body(None, embed=True),
    assignment_ids: list[int] = Body(None, embed=True),
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Start analysis for one assignment (`assignment_id`) or a batch
    (`assignment_ids`).  Only the owning student can trigger analysis.
    Requires:  Authorization: Bearer <token>
    """
    if assignment_id is not None:
        res = await db.execute(
            select(Assignment).filter(
                Assignment.id == assignment_id,
                Assignment.student_id == current_student.id,
            )
        )
        assignment = res.scalars().first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        try:
            summary = await analyze_assignment_and_save(db, assignment, top_k_sources=5)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

        return {"status": "done", "result": summary}

    elif assignment_ids:
        assignments = []
        for aid in assignment_ids:
            res = await db.execute(
                select(Assignment).filter(
                    Assignment.id == aid,
                    Assignment.student_id == current_student.id,
                )
            )
            assignment = res.scalars().first()
            if assignment:
                assignments.append(assignment)

        if not assignments:
            raise HTTPException(status_code=404, detail="No valid assignments found")

        results = []
        for assignment in assignments:
            try:
                summary = await analyze_assignment_and_save(db, assignment, top_k_sources=5)
                results.append({"assignment_id": assignment.id, "result": summary})
            except Exception as e:
                results.append({"assignment_id": assignment.id, "error": str(e)})

        return {"status": "done", "results": results}

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'assignment_id' (int) or 'assignment_ids' (list of int)",
        )


@router.get("/{assignment_id}", summary="Get the latest analysis result for an assignment")
async def get_analysis_for_assignment(
    assignment_id: int,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the most recent AnalysisResult for an assignment.
    Only the owning student can view results.
    Requires:  Authorization: Bearer <token>
    """
    # Ensure the assignment belongs to the current student
    res = await db.execute(
        select(Assignment).filter(
            Assignment.id == assignment_id,
            Assignment.student_id == current_student.id,
        )
    )
    assignment = res.scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    res = await db.execute(
        select(AnalysisResult)
        .filter(AnalysisResult.assignment_id == assignment_id)
        .order_by(AnalysisResult.analyzed_at.desc())
    )
    analysis = res.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No analysis found for that assignment. Run /analysis/start first.",
        )

    return {
        "id":                       analysis.id,
        "assignment_id":            analysis.assignment_id,
        "suggested_sources":        analysis.suggested_sources,
        "plagiarism_score":         analysis.plagiarism_score,
        "flagged_sections":         analysis.flagged_sections,
        "research_suggestions":     analysis.research_suggestions,
        "citation_recommendations": analysis.citation_recommendations,
        "confidence_score":         analysis.confidence_score,
        "analyzed_at":              analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
    }

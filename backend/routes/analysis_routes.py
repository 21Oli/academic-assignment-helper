# backend/routes/analysis_routes.py
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.logger import get_logger
from backend.models import Assignment, AnalysisResult, Student
from backend.rag_service import analyze_assignment_and_save
from backend.deps import get_current_student
from backend.schemas import (
    StartAnalysisRequest,
    StartAnalysisSingleResponse,
    StartAnalysisBatchResponse,
    SingleAnalysisResult,
    BatchResultItem,
    AnalysisResultResponse,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])
_limiter = Limiter(key_func=get_remote_address)
logger = get_logger(__name__)


@router.post(
    "/start",
    summary="Trigger analysis for one or more assignments",
    responses={
        200: {"description": "Single assignment result", "model": StartAnalysisSingleResponse},
        202: {"description": "Batch analysis results",  "model": StartAnalysisBatchResponse},
    },
)
@_limiter.limit("10/minute")
async def start_analysis(
    request: Request,  # required by slowapi
    body: StartAnalysisRequest,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Provide either `assignment_id` (int) for a single analysis or
    `assignment_ids` (list) for batch analysis.
    Only assignments belonging to the authenticated student are processed.
    Requires: Authorization: Bearer <token>
    """
    if body.assignment_id is not None:
        res = await db.execute(
            select(Assignment).filter(
                Assignment.id == body.assignment_id,
                Assignment.student_id == current_student.id,
            )
        )
        assignment = res.scalars().first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        try:
            summary = await analyze_assignment_and_save(db, assignment, top_k_sources=5)
        except Exception as e:
            import traceback
            logger.error("analysis.route_failed", assignment_id=body.assignment_id, error=str(e), traceback=traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

        return StartAnalysisSingleResponse(
            status="done",
            result=SingleAnalysisResult(**summary),
        )

    elif body.assignment_ids:
        assignments = []
        for aid in body.assignment_ids:
            res = await db.execute(
                select(Assignment).filter(
                    Assignment.id == aid,
                    Assignment.student_id == current_student.id,
                )
            )
            a = res.scalars().first()
            if a:
                assignments.append(a)

        if not assignments:
            raise HTTPException(status_code=404, detail="No valid assignments found")

        results = []
        for assignment in assignments:
            try:
                summary = await analyze_assignment_and_save(db, assignment, top_k_sources=5)
                results.append(BatchResultItem(
                    assignment_id=assignment.id,
                    result=SingleAnalysisResult(**summary),
                ))
            except Exception as e:
                results.append(BatchResultItem(
                    assignment_id=assignment.id,
                    error=str(e),
                ))

        return StartAnalysisBatchResponse(status="done", results=results)

    raise HTTPException(
        status_code=400,
        detail="Provide either 'assignment_id' (int) or 'assignment_ids' (list of int)",
    )


@router.get(
    "/{assignment_id}",
    response_model=AnalysisResultResponse,
    summary="Get the latest analysis result for an assignment",
)
async def get_analysis_for_assignment(
    assignment_id: int,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the most recent AnalysisResult for an assignment.
    Only the owning student can view results.
    Requires: Authorization: Bearer <token>
    """
    res = await db.execute(
        select(Assignment).filter(
            Assignment.id == assignment_id,
            Assignment.student_id == current_student.id,
        )
    )
    if not res.scalars().first():
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
            detail="No analysis found. Run POST /analysis/start first.",
        )

    return AnalysisResultResponse(
        id=analysis.id,
        assignment_id=analysis.assignment_id,
        suggested_sources=analysis.suggested_sources,
        plagiarism_score=analysis.plagiarism_score,
        flagged_sections=analysis.flagged_sections,
        research_suggestions=analysis.research_suggestions,
        citation_recommendations=analysis.citation_recommendations,
        confidence_score=analysis.confidence_score,
        analyzed_at=analysis.analyzed_at,
    )

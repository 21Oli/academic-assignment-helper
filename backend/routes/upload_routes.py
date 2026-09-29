# backend/routes/upload_routes.py
import os
import mimetypes
import aiofiles
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Assignment, Student
from backend.database import get_db
from backend.deps import get_current_student
from backend.schemas import UploadResponse

import PyPDF2
import docx

router = APIRouter(prefix="/upload", tags=["Assignments"])

UPLOAD_DIR = "/app/uploads"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


async def extract_text(file_path: str, filename: str, content: bytes) -> str:
    """Best-effort text extraction from PDF, DOCX, or plain text."""
    text = ""
    mime_type, _ = mimetypes.guess_type(filename)
    try:
        if mime_type and "text" in mime_type:
            text = content.decode("utf-8", errors="ignore")
        elif filename.lower().endswith(".pdf"):
            reader = PyPDF2.PdfReader(file_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
        elif filename.lower().endswith(".docx"):
            doc = docx.Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"⚠️  Text extraction failed: {e}")
    return text


@router.post(
    "/",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload an assignment file (PDF, DOCX, or plain text)",
)
async def upload_assignment(
    file: UploadFile = File(...),
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a .pdf, .docx, or plain-text assignment.
    Requires: Authorization: Bearer <token>
    Returns: assignment_id to use with POST /analysis/start
    """
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    safe_filename = os.path.basename(file.filename or "upload")
    file_path = os.path.join(UPLOAD_DIR, f"{current_student.id}_{safe_filename}")

    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    text = await extract_text(file_path, safe_filename, content)

    assignment = Assignment(
        student_id=current_student.id,
        filename=safe_filename,
        file_path=file_path,
        original_text=text or None,
        topic=safe_filename.rsplit(".", 1)[0],
        word_count=len(text.split()) if text else 0,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    # Notify n8n asynchronously — upload succeeds regardless
    if N8N_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(N8N_WEBHOOK_URL, json={
                    "assignment_id": assignment.id,
                    "file_path": file_path,
                    "student_email": current_student.email,
                })
        except Exception as e:
            print(f"⚠️  Failed to trigger n8n: {e}")

    return UploadResponse(
        success=True,
        message="File uploaded successfully",
        assignment_id=assignment.id,
    )

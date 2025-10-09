# backend/routes/upload_routes.py
import os
import mimetypes
import aiofiles
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import Assignment, Student
from backend.database import get_db

# optional extraction libs (ensure these are in requirements)
import PyPDF2
import docx

router = APIRouter(prefix="/upload", tags=["Assignments"])

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "changeme")
ALGORITHM = "HS256"
UPLOAD_DIR = "/app/uploads"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")  # e.g. http://n8n:5678/webhook/assignment

os.makedirs(UPLOAD_DIR, exist_ok=True)


async def extract_text(file_path: str, filename: str, content: bytes) -> str:
    text = ""
    mime_type, _ = mimetypes.guess_type(filename)
    try:
        # plain text files (txt, csv, etc.)
        if mime_type and "text" in mime_type:
            text = content.decode("utf-8", errors="ignore")
        # PDF
        elif filename.lower().endswith(".pdf"):
            reader = PyPDF2.PdfReader(file_path)
            text = "".join((page.extract_text() or "") for page in reader.pages)
        # DOCX
        elif filename.lower().endswith(".docx"):
            doc = docx.Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        # fallback: small binary -> try utf-8
        else:
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
    except Exception as e:
        # don't crash upload on extraction errors
        print("⚠️ Text extraction failed:", e)
        text = ""
    return text


@router.post("/")
async def upload_assignment(
    token: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Verify JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Find student
    result = await db.execute(select(Student).filter(Student.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # save file (async)
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Optional: enforce max size (e.g. 10MB)
    content = await file.read()
    max_bytes = 20 * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    # extract text (best-effort)
    text = await extract_text(file_path, safe_filename, content)

    # create DB record
    assignment = Assignment(
        student_id=user.id,
        filename=safe_filename,
        file_path=file_path,
        original_text=text or None,
        topic=safe_filename.rsplit(".", 1)[0],
        word_count=len(text.split()) if text else 0
    )

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    # notify n8n (async)
    if N8N_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(N8N_WEBHOOK_URL, json={
                    "assignment_id": assignment.id,
                    "file_path": file_path,
                    "student_email": user.email
                })
        except Exception as e:
            # just log the failure; uploading succeeded
            print("⚠️ Failed to trigger n8n:", e)

    return {
        "success": True,
        "message": "File uploaded successfully",
        "assignment_id": assignment.id
    }

"""
Shared FastAPI dependencies.

All protected routes should use `get_current_student` as a Depends() argument.
Tokens are expected in the standard Authorization: Bearer <token> header.
"""
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import Student

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "changeme")
ALGORITHM = "HS256"

# FastAPI's built-in Bearer scheme — adds a padlock in /docs and reads
# the Authorization header automatically.
_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Student:
    """
    Decode the JWT from the Authorization: Bearer header and return the
    matching Student row.  Raises HTTP 401 on any failure.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Student).filter(Student.email == email))
    student = result.scalars().first()
    if not student:
        raise credentials_exception

    return student

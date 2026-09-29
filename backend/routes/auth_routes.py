# backend/routes/auth_routes.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models import Student
from backend.auth import get_password_hash, verify_password, create_access_token
from backend.database import get_db
from backend.deps import get_current_student

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", summary="Register a new student account")
async def register_user(
    email: str,
    password: str,
    full_name: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).filter(Student.email == email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = Student(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}


@router.post("/login", summary="Log in and receive a JWT access token")
async def login_user(
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).filter(Student.email == email))
    user = result.scalars().first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", summary="Get the current authenticated student's profile")
async def get_me(current_student: Student = Depends(get_current_student)):
    """
    Returns the profile of the currently authenticated student.
    Requires:  Authorization: Bearer <token>
    """
    return {
        "id":         current_student.id,
        "email":      current_student.email,
        "full_name":  current_student.full_name,
        "created_at": current_student.created_at.isoformat() if current_student.created_at else None,
    }

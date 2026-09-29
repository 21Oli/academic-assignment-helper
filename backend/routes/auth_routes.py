# backend/routes/auth_routes.py
from fastapi import APIRouter, HTTPException, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models import Student
from backend.auth import get_password_hash, verify_password, create_access_token
from backend.database import get_db
from backend.deps import get_current_student
from backend.schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, TokenResponse,
    StudentProfile,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Route-level limiter — key by IP address
_limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
@_limiter.limit("10/minute")
async def register_user(
    request: Request,  # required by slowapi
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).filter(Student.email == body.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = Student(
        email=body.email,
        password_hash=get_password_hash(body.password),
        full_name=body.full_name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return RegisterResponse(message="User registered successfully", user_id=new_user.id)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
)
@_limiter.limit("20/minute")
async def login_user(
    request: Request,  # required by slowapi
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Student).filter(Student.email == body.email))
    user = result.scalars().first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=StudentProfile,
    summary="Get the current authenticated student's profile",
)
async def get_me(current_student: Student = Depends(get_current_student)):
    """Requires: Authorization: Bearer <token>"""
    return StudentProfile.model_validate(current_student)

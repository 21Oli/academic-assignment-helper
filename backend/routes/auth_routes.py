from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models import Student
from backend.auth import get_password_hash, verify_password, create_access_token
from backend.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

#  Register new user
@router.post("/register")
async def register_user(email: str, password: str, full_name: str, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(Student).filter(Student.email == email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    new_user = Student(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}

#  Login existing user
@router.post("/login")
async def login_user(email: str, password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).filter(Student.email == email))
    user = result.scalars().first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

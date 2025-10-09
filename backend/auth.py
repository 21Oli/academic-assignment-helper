import os
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import secrets

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# bcrypt only supports up to 72 bytes of input
MAX_PASSWORD_LEN = 72

def get_password_hash(password: str) -> str:
    password = password.encode("utf-8")[:MAX_PASSWORD_LEN].decode("utf-8", errors="ignore")
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    plain = plain.encode("utf-8")[:MAX_PASSWORD_LEN].decode("utf-8", errors="ignore")
    return pwd_ctx.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

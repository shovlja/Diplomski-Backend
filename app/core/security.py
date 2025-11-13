# app/core/security.py
from datetime import datetime, timedelta
from uuid import UUID
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(sub: str | UUID) -> str:
    # uvijek u token stavljamo string
    subject = str(sub)
    expire = datetime.utcnow() + timedelta(seconds=settings.jwt_expires_in)
    payload = {"sub": subject, "exp": expire}
    # koristi isti ključ i algoritam kao u get_current_user
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_alg)

# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import SystemRole, User
from app.schemas.user import UserOut
from app.schemas.auth import RegisterIn, TokenOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()

    exists = await db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        system_role=SystemRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user  # Pydantic filtrira po UserOut

@router.post("/login", response_model=TokenOut)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    email = form.username.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    # SUBJECT = user.id (UUID kao string)  ← front/guard očekuju /me po tokenu
    token = create_access_token(sub=str(user.id))
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    # stateless JWT: front briše token; ovde samo 204
    return

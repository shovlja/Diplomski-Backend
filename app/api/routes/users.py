from __future__ import annotations

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.security import hash_password
from app.models.user import User, SystemRole
from app.schemas.user import (
    UserOut,
    UserCreate,
    UserUpdate,
    UserRoleUpdate,
    UserActiveUpdate,
    UsersPage,
    RoleFilter,
    StatusFilter,
    SortKey,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# Ako kasnije dodaš backend admin guard, ovde ga lako ubaciš:
# from app.api.deps import get_current_user, require_admin
# dependencies=[Depends(require_admin)] na svim rutama


def _filters(q: str | None, role: RoleFilter, status: StatusFilter):
    conds = []
    if q:
        qq = f"%{q.lower()}%"
        conds.append(
            or_(
                func.lower(User.display_name).like(qq),
                func.lower(User.email).like(qq),
            )
        )
    if role != "all":
        conds.append(
            User.system_role == (SystemRole.ADMIN if role == "admin" else SystemRole.USER)
        )
    if status != "all":
        conds.append(User.is_active == (status == "active"))
    return conds


def _order_by(sort: SortKey):
    match sort:
        case "created_asc":
            return User.created_at.asc()
        case "name_asc":
            return User.display_name.asc()
        case "name_desc":
            return User.display_name.desc()
        case "email_asc":
            return User.email.asc()
        case "email_desc":
            return User.email.desc()
        case _:
            return User.created_at.desc()


@router.get("", response_model=UsersPage)
async def list_users(
    q: str | None = Query(default=None, description="search in name/email"),
    role: RoleFilter = Query(default="all"),
    status: StatusFilter = Query(default="all"),
    sort: SortKey = Query(default="created_desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    conds = _filters(q, role, status)

    stmt = (
        select(User)
        .where(*conds)
        .order_by(_order_by(sort))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total_stmt = select(func.count()).select_from(select(User).where(*conds).subquery())

    res = await db.execute(stmt)
    items = list(res.scalars().all())
    total = (await db.execute(total_stmt)).scalar_one()

    # Pydantic UserOut (orm_mode/from_attributes) odradi serialize
    return UsersPage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    email = payload.email.strip().lower()

    # unique email
    exists = await db.scalar(select(User).where(User.email == email))
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        avatar_url=payload.avatar_url,
        system_role=payload.system_role,
        is_active=payload.is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID, payload: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserOut)
async def set_user_role(
    user_id: UUID, payload: UserRoleUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.system_role = payload.system_role
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserOut)
async def set_user_active(
    user_id: UUID, payload: UserActiveUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return

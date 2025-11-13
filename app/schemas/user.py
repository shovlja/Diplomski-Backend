from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum

class SystemRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

RoleFilter = Literal["all", "admin", "user"]
StatusFilter = Literal["all", "active", "inactive"]
SortKey = Literal[
    "created_desc",
    "created_asc",
    "name_asc",
    "name_desc",
    "email_asc",
    "email_desc",
]

class UserOut(BaseModel):
    id: UUID
    display_name: str
    email: EmailStr
    system_role: SystemRole     # ← ostaje
    is_active: bool
    avatar_url: str | None = None
    created_at: datetime

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    avatar_url: Optional[str] = None
    system_role: SystemRole = SystemRole.USER
    is_active: bool = True

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None

class UserRoleUpdate(BaseModel):
    system_role: SystemRole

class UserActiveUpdate(BaseModel):
    is_active: bool

class UsersPage(BaseModel):
    items: list["UserOut"]
    total: int
    page: int
    page_size: int
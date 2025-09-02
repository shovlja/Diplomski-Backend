from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID
from datetime import datetime
from enum import Enum

class SystemRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

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

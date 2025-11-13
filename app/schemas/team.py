from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from enum import Enum
from datetime import datetime
from uuid import UUID


class TeamRole(str, Enum):
    owner = "owner"
    manager = "manager"
    developer = "developer"


class UserBrief(BaseModel):
    id: UUID
    display_name: str
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True


class TeamMemberUserLite(BaseModel):
    # ⬅️ ranije: str — sada dosledno UUID
    id: UUID
    display_name: str
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True


class TeamMemberOut(BaseModel):
    id: int
    # ⬅️ ostaje UUID (bitno da FE ne pretvara u number!)
    user_id: UUID
    role: TeamRole
    user: Optional[UserBrief] = None

    class Config:
        orm_mode = True


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class TeamOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_archived: bool
    members: List[TeamMemberOut] = []

    class Config:
        orm_mode = True


class InviteCreate(BaseModel):
    email: EmailStr


class TeamInviteOut(BaseModel):
    id: int
    team_id: int
    email: EmailStr
    # ⬅️ ranije int — korisnici su UUID
    invited_by: UUID
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


# Dozvoli samo non-owner role za PATCH members/{user_id}
NonOwnerRole = Literal["manager", "developer"]


class MemberRoleUpdate(BaseModel):
    role: NonOwnerRole

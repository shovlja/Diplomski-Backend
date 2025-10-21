from pydantic import BaseModel, EmailStr
from typing import Optional, List
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
    id: str
    display_name: str
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True


class TeamMemberOut(BaseModel):
    id: int
    user_id: UUID              # ⬅️ OBAVEZNO UUID, ne str
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
    invited_by: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class MemberRoleUpdate(BaseModel):
    role: TeamRole

from typing import Union, Literal
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class NotificationKind(str, Enum):
    team_invite = "team_invite"
    team_joined = "team_joined"
    team_kicked = "team_kicked"
    team_role_changed = "team_role_changed"
    invite_accepted = "invite_accepted"
    member_left = "member_left"


class TeamInvitePayload(BaseModel):
    team_id: int
    team_name: str
    inviter_name: str


class TeamJoinedPayload(BaseModel):
    team_id: int
    team_name: str


class TeamKickedPayload(BaseModel):
    team_id: int
    team_name: str


class TeamRoleChangedPayload(BaseModel):
    team_id: int
    team_name: str
    role: Literal["developer", "manager", "owner"]


class InviteAcceptedPayload(BaseModel):
    team_id: int
    team_name: str
    actor_display_name: str


class MemberLeftPayload(BaseModel):
    team_id: int
    team_name: str
    actor_display_name: str


PayloadUnion = Union[
    TeamInvitePayload,
    TeamJoinedPayload,
    TeamKickedPayload,
    TeamRoleChangedPayload,
    InviteAcceptedPayload,
    MemberLeftPayload,
]


class NotificationOut(BaseModel):
    id: int
    kind: NotificationKind
    created_at: datetime
    is_read: bool
    payload: PayloadUnion

    class Config:
        orm_mode = True

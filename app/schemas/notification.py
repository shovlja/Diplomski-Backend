# app/schemas/notification.py
from typing import Union
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class NotificationKind(str, Enum):
    team_invite = "team_invite"
    team_joined = "team_joined"


class TeamInvitePayload(BaseModel):
    team_id: int
    team_name: str
    inviter_name: str


class TeamJoinedPayload(BaseModel):
    team_id: int
    team_name: str


class NotificationOut(BaseModel):
    id: int
    kind: NotificationKind
    created_at: datetime
    is_read: bool
    payload: Union[TeamInvitePayload, TeamJoinedPayload]

    class Config:
        orm_mode = True

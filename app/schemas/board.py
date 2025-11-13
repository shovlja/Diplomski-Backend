from typing import Optional, Literal, List
from pydantic import BaseModel, Field

BoardPrivacy = Literal["private", "team"] 

class MemberPreview(BaseModel):
    id: str | int
    name: str
    avatarUrl: Optional[str] = None

class BoardOut(BaseModel):
    id: int
    title: str
    teamName: Optional[str] = None
    privacy: BoardPrivacy
    isStarred: bool
    lastActivity: str
    cover: Optional[str] = None
    members: List[MemberPreview] = []
    tags: List[str] = []
    isOwner: bool = False

class BoardCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    privacy: BoardPrivacy
    team_id: Optional[int] = None
    tags: Optional[List[str]] = None

class BoardUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    privacy: Optional[BoardPrivacy] = None  
    team_id: Optional[int] = None
    tags: Optional[List[str]] = None       
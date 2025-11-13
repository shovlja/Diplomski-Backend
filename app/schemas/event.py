from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    starts_at: datetime

class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    starts_at: Optional[datetime] = None

class EventOut(BaseModel):
    id: int
    title: str
    starts_at: datetime
    created_at: datetime

    class Config:
        orm_mode = True

class CalendarOut(BaseModel):
    dates: List[str]
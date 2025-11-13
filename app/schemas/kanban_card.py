from datetime import datetime
from typing import List, Optional
from .kanban_label import CamelModel, LabelOut, OkOut

class CommentOut(CamelModel):
    id: int
    author: str
    created_at: datetime
    text: str

class CardOut(CamelModel):
    id: int
    title: str
    description: Optional[str] = None
    position: int
    due_date: Optional[datetime] = None
    due_complete: bool
    labels: List[LabelOut] = []
    checklists: List  = []   # popuni po potrebi ChecklistOut
    comments: List[CommentOut] = []

# -------- inputs / minimal outputs --------
class CardCreateIn(CamelModel):
    list_id: int
    title: str

class CardCreateOut(CamelModel):
    id: int
    position: int

class CardMoveIn(CamelModel):
    to_list_id: int
    target_index: int

class CardMoveOut(CamelModel):
    list_id: int
    position: int

class CardPatchIn(CamelModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None          # ISO string
    due_complete: Optional[bool] = None
    label_ids: Optional[List[int]] = None

class CommentCreateIn(CamelModel):
    card_id: int
    author: str
    text: str

class CommentCreateOut(CamelModel):
    id: int
    created_at: datetime

class CommentPatchIn(CamelModel):
    text: str

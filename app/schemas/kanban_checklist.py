from typing import List
from pydantic import BaseModel
from .kanban_label import CamelModel

class ChecklistItemOut(CamelModel):
    id: int
    text: str
    done: bool

class ChecklistOut(CamelModel):
    id: int
    title: str
    items: List[ChecklistItemOut] = []

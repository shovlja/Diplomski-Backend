from typing import List
from .kanban_label import CamelModel
from .kanban_list import ListOut

class BoardContentOut(CamelModel):
    id: int
    title: str
    lists: List[ListOut] = []

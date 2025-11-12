from typing import List, Optional
from .kanban_label import CamelModel

class ListOut(CamelModel):
    id: int
    title: str
    position: int
    cards: List = []  # popuni po potrebi CardOut

# -------- inputs / minimal outputs --------
class ListCreateIn(CamelModel):
    board_id: int
    title: str

class ListMinimalOut(CamelModel):
    id: int
    position: int

class ListRenameIn(CamelModel):
    title: str

class ListMoveIn(CamelModel):
    board_id: int
    target_index: int

class ListMoveOut(CamelModel):
    position: int

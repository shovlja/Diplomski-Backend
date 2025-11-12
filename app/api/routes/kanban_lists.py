from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board import Board
from app.models.board_list import BoardList
from app.services.ordering import new_list_position

# ---------------- /api/v1/lists (PATCH/DELETE) ----------------
router = APIRouter(prefix="/api/v1/lists", tags=["kanban-lists"])

@router.patch("/{list_id}")
async def update_list(list_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    l = await db.get(BoardList, list_id)
    if not l:
        raise HTTPException(status_code=404, detail="List not found")

    if "title" in payload and payload["title"] is not None:
        t = (payload["title"] or "").strip()
        if not t:
            raise HTTPException(status_code=422, detail="Title cannot be empty")
        l.title = t

    if "position" in payload and payload["position"] is not None:
        try:
            l.position = int(payload["position"])
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid position")

    await db.commit()
    await db.refresh(l)
    return {"id": l.id, "title": l.title, "position": l.position, "cards": []}

@router.delete("/{list_id}", status_code=204)
async def delete_list(list_id: int, db: AsyncSession = Depends(get_db)):
    l = await db.get(BoardList, list_id)
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    await db.delete(l)
    await db.commit()
    return

# -------- /api/v1/boards (create + reorder lists na boardu) --------
bridge = APIRouter(prefix="/api/v1/boards", tags=["kanban-lists"])

@bridge.post("/{board_id}/lists")
async def create_list(board_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    b = await db.get(Board, board_id)
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")

    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title is required")

    pos = await new_list_position(db, board_id=board_id, target_index=10**9)
    l = BoardList(board_id=board_id, title=title, position=pos)
    db.add(l)
    await db.commit()
    await db.refresh(l)

    return {"id": l.id, "title": l.title, "position": l.position, "cards": []}

@bridge.post("/{board_id}/lists/reorder", status_code=204)
async def reorder_lists(board_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    b = await db.get(Board, board_id)
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")

    ids = payload.get("list_ids") or []
    if not isinstance(ids, list):
        raise HTTPException(status_code=422, detail="list_ids must be a list")

    for i, lid in enumerate(ids):
        await db.execute(
            update(BoardList)
            .where(BoardList.id == int(lid), BoardList.board_id == board_id)
            .values(position=(i + 1) * 65535)
        )
    await db.commit()
    return

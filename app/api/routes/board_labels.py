# app/api/routes/board_labels.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board import Board
from app.models.board_label import BoardLabel, CardLabel  # BoardLabel = tabela board_labels, CardLabel = pivot
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["Board Labels"])

def _normalize_color(c: str | None) -> str:
    if not c:
        return "#94a3b8"  # neka neutralna siva
    c = c.strip()
    if not c.startswith("#"):
        c = "#" + c
    if len(c) not in (4, 7):
        raise HTTPException(422, detail="Invalid color format")
    return c.lower()


@router.get("/boards/{board_id}/labels")
async def list_board_labels(board_id: int, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    b = await db.get(Board, board_id)
    if not b:
        raise HTTPException(404, "Board not found")

    rows = (await db.execute(select(BoardLabel).where(BoardLabel.board_id == board_id))).scalars().all()
    return [{"id": r.id, "name": r.name, "color": r.color} for r in rows]


@router.post("/boards/{board_id}/labels", status_code=201)
async def create_board_label(
    board_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    b = await db.get(Board, board_id)
    if not b:
        raise HTTPException(404, "Board not found")

    name = (payload.get("name") or "").strip()
    color = _normalize_color(payload.get("color"))
    if not name:
        raise HTTPException(422, "Name is required")

    lbl = BoardLabel(board_id=board_id, name=name, color=color)
    db.add(lbl)
    await db.commit()
    await db.refresh(lbl)
    return {"id": lbl.id, "name": lbl.name, "color": lbl.color}


@router.patch("/labels/{label_id}")
async def update_label(
    label_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    lbl = await db.get(BoardLabel, label_id)
    if not lbl:
        raise HTTPException(404, "Label not found")

    if "name" in payload:
        nm = (payload.get("name") or "").strip()
        if not nm:
            raise HTTPException(422, "Name is required")
        lbl.name = nm
    if "color" in payload:
        lbl.color = _normalize_color(payload.get("color"))

    await db.commit()
    return {"id": lbl.id, "name": lbl.name, "color": lbl.color}


@router.delete("/labels/{label_id}", status_code=204)
async def delete_label(label_id: int, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    lbl = await db.get(BoardLabel, label_id)
    if not lbl:
        raise HTTPException(404, "Label not found")

    # očisti pivot (card_labels) pa obriši label
    await db.execute(delete(CardLabel).where(CardLabel.label_id == label_id))
    await db.delete(lbl)
    await db.commit()
    return

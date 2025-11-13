from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board_label import BoardLabel

router = APIRouter(prefix="/api/v1/labels", tags=["kanban-labels"])

@router.get("/by-board/{board_id}")
async def list_labels(board_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(BoardLabel).where(BoardLabel.board_id == board_id))).scalars().all()
    return rows

@router.patch("/{label_id}")
async def patch_label(label_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    lab = await db.get(BoardLabel, label_id)
    if not lab:
        raise HTTPException(404, "Label not found")
    if "name" in payload and payload["name"] is not None:
        lab.name = (payload["name"] or "").strip()
    if "color" in payload and payload["color"] is not None:
        lab.color = payload["color"]
    await db.commit(); await db.refresh(lab)
    return {"id": lab.id, "name": lab.name, "color": lab.color}

@router.delete("/{label_id}", status_code=204)
async def delete_label(label_id: int, db: AsyncSession = Depends(get_db)):
    lab = await db.get(BoardLabel, label_id)
    if not lab:
        raise HTTPException(404, "Label not found")
    await db.delete(lab); await db.commit()
    return

# bridge: /api/v1/boards/{board_id}/labels (create)
bridge = APIRouter(prefix="/api/v1/boards", tags=["kanban-labels"])

@bridge.post("/{board_id}/labels")
async def create_label(board_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    color = payload.get("color") or "#9CA3AF"
    if not name:
        raise HTTPException(422, "Name is required")

    lab = BoardLabel(board_id=board_id, name=name, color=color)
    db.add(lab); await db.commit(); await db.refresh(lab)
    return {"id": lab.id, "name": lab.name, "color": lab.color}

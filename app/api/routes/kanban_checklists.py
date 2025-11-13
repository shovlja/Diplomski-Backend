from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board_card import BoardCard
from app.models.board_checklist import BoardChecklist, BoardChecklistItem

router = APIRouter(tags=["kanban-checklists"])

@router.post("/api/v1/cards/{card_id}/checklists")
async def create_checklist(card_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    c = await db.get(BoardCard, card_id)
    if not c:
        raise HTTPException(404, "Card not found")
    title = (payload.get("title") or "").strip() or "Checklist"
    ch = BoardChecklist(card_id=card_id, title=title)
    db.add(ch); await db.commit(); await db.refresh(ch)
    return {"id": str(ch.id), "title": ch.title, "items": []}

@router.delete("/api/v1/checklists/{checklist_id}", status_code=204)
async def delete_checklist(checklist_id: int, db: AsyncSession = Depends(get_db)):
    ch = await db.get(BoardChecklist, checklist_id)
    if not ch:
        raise HTTPException(404, "Checklist not found")
    await db.delete(ch); await db.commit()
    return

@router.post("/api/v1/checklists/{checklist_id}/items")
async def add_item(checklist_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    ch = await db.get(BoardChecklist, checklist_id)
    if not ch:
        raise HTTPException(404, "Checklist not found")
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(422, "Text is required")
    it = BoardChecklistItem(checklist_id=checklist_id, text=text, done=False)
    db.add(it); await db.commit(); await db.refresh(it)
    return {"id": str(it.id), "text": it.text, "done": it.done}

@router.patch("/api/v1/checklist-items/{item_id}")
async def update_item(item_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    it = await db.get(BoardChecklistItem, item_id)
    if not it:
        raise HTTPException(404, "Item not found")
    if "text" in payload and payload["text"] is not None:
        it.text = (payload["text"] or "").strip()
    if "done" in payload and payload["done"] is not None:
        it.done = bool(payload["done"])
    await db.commit(); await db.refresh(it)
    return {"id": str(it.id), "text": it.text, "done": it.done}

from __future__ import annotations
from datetime import datetime
from typing import Iterable, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board_card import BoardCard
from app.models.board_list import BoardList
from app.models.board_label import CardLabel, BoardLabel
from app.models.board_comment import BoardComment
from app.models.board_member import CardMember
from app.models.team import TeamMember
from app.services.ordering import new_card_position

# ---------------- /api/v1/cards (patch + aux) ----------------
router = APIRouter(prefix="/api/v1/cards", tags=["kanban-cards"])

@router.patch("/{card_id}")
async def patch_card(card_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    c = await db.get(BoardCard, card_id)
    if not c:
        raise HTTPException(404, "Card not found")

    if "title" in payload and payload["title"] is not None:
        c.title = (payload["title"] or "").strip()
    if "description" in payload:
        c.description = payload["description"]
    if "dueDate" in payload:
        iso = payload["dueDate"]
        c.due_date = None if not iso else datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if "dueComplete" in payload:
        c.due_complete = bool(payload["dueComplete"])

    await db.commit()
    return {"ok": True}

@router.put("/{card_id}/labels", status_code=204)
async def replace_labels(card_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    ids = payload.get("label_ids") or []
    if not isinstance(ids, list):
        raise HTTPException(422, "label_ids must be list")

    card = await db.get(BoardCard, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    lst = await db.get(BoardList, card.list_id)
    if not lst:
        raise HTTPException(404, "List not found for card")

    # validacija da sve labele pripadaju istom boardu
    stmt = select(BoardLabel.id).where(
        BoardLabel.id.in_(ids),
        BoardLabel.board_id == lst.board_id,
    )
    valid_ids = set((await db.execute(stmt)).scalars().all())
    invalid = [x for x in ids if x not in valid_ids]
    if invalid:
        raise HTTPException(409, f"Labels {invalid} do not belong to this board")

    await db.execute(delete(CardLabel).where(CardLabel.card_id == card_id))
    for lid in valid_ids:
        db.add(CardLabel(card_id=card_id, label_id=int(lid)))
    await db.commit()
    return

def _looks_like_uuid(s: str) -> Optional[str]:
    try:
        return str(uuid.UUID(str(s)))
    except Exception:
        return None

def _normalize_member_ids(raw_ids: Iterable[object]) -> tuple[list[str], list[int]]:
    """Vraća (uuid_str_list, membership_id_list)."""
    uuids: list[str] = []
    mem_ids: list[int] = []
    for x in raw_ids:
        s = str(x)
        u = _looks_like_uuid(s)
        if u:
            uuids.append(u)
            continue
        # nije UUID → možda je TeamMember.id
        try:
            mem_ids.append(int(s))
        except ValueError:
            # ignoriši sve što nije ni UUID ni int
            pass
    return uuids, mem_ids

@router.put("/{card_id}/members", status_code=204)
async def set_members(card_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Prihvata:
      - member_ids: list[str] — može mešano: User UUID ili TeamMember.id
    Ne menjamo modele. Ako je ID membership (npr. '40'), mapiramo ga na User UUID
    preko TeamMember.user_id i samo validne UUID vrednosti upisujemo u card_members.
    """
    raw = payload.get("member_ids") or payload.get("memberIds") or []
    if not isinstance(raw, list):
        raise HTTPException(422, "member_ids must be list")

    # razdvoji UUID-ove od membership ID-jeva
    uuid_ids, membership_ids = _normalize_member_ids(raw)

    # mapiraj membership → user_uuid (tip u modelu nas ne zanima; castujemo u str i validiramo)
    if membership_ids:
        rows = await db.execute(
            select(TeamMember.id, TeamMember.user_id).where(TeamMember.id.in_(membership_ids))
        )
        for _, user_id in rows.all():
            u = _looks_like_uuid(str(user_id))
            if u:
                uuid_ids.append(u)
            # ako nije validan UUID (npr. čist broj), preskačemo da ne padne INSERT

    # deduplikuj i očisti postojeće
    final_ids = sorted(set(uuid_ids))
    await db.execute(delete(CardMember).where(CardMember.card_id == card_id))
    for u in final_ids:
        db.add(CardMember(card_id=card_id, user_id=u))
    await db.commit()
    return

# ------------- /api/v1/lists (create + reorder cards) -------------
bridge = APIRouter(prefix="/api/v1/lists", tags=["kanban-cards"])

@bridge.post("/{list_id}/cards")
async def create_card(list_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    l = await db.get(BoardList, list_id)
    if not l:
        raise HTTPException(404, "List not found")

    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(422, "Title is required")

    pos = await new_card_position(db, to_list_id=list_id, target_index=10**9)
    c = BoardCard(list_id=list_id, title=title, position=pos)
    db.add(c); await db.commit(); await db.refresh(c)

    return {
        "id": c.id,
        "title": c.title,
        "position": c.position,
        "description": c.description,
        "due_date": c.due_date.isoformat() if c.due_date else None,
        "due_complete": c.due_complete,
        "labels": [],
        "checklists": [],
        "comments": [],
    }

@bridge.post("/{list_id}/cards/reorder", status_code=204)
async def reorder_cards(list_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    ids = payload.get("card_ids") or []
    if not isinstance(ids, list):
        raise HTTPException(422, "card_ids must be list")

    for i, cid in enumerate(ids):
        await db.execute(
            update(BoardCard)
            .where(BoardCard.id == int(cid))
            .values(list_id=list_id, position=(i + 1) * 65535)
        )
    await db.commit()
    return

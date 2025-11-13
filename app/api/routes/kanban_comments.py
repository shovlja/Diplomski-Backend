from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.board_comment import BoardComment
from app.schemas.kanban_card import CommentCreateIn, CommentCreateOut, CommentPatchIn
from app.schemas.kanban_label import OkOut

router = APIRouter(prefix="/api/v1/comments", tags=["kanban-comments"])

def _me_name(me: User) -> str:
    return (me.display_name or me.username or (me.email.split("@")[0] if me.email else "User")).strip()

@router.post("", response_model=CommentCreateOut, response_model_by_alias=True)
async def add_comment(payload: CommentCreateIn, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    # ignoriši author iz payload-a, uvek koristi ulogovanog
    c = BoardComment(card_id=payload.card_id, author=_me_name(me), text=payload.text)
    db.add(c); await db.commit(); await db.refresh(c)
    return CommentCreateOut(id=c.id, created_at=c.created_at)

@router.patch("/{comment_id}", response_model=OkOut, response_model_by_alias=True)
async def edit_comment(comment_id: int, payload: CommentPatchIn, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    c = await db.get(BoardComment, comment_id)
    if not c: raise HTTPException(404, "Comment not found")
    if c.author != _me_name(me): raise HTTPException(403, "You can edit only your comment")
    c.text = payload.text
    await db.commit()
    return {"ok": True}

@router.delete("/{comment_id}", response_model=OkOut, response_model_by_alias=True)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    c = await db.get(BoardComment, comment_id)
    if not c: raise HTTPException(404, "Comment not found")
    if c.author != _me_name(me): raise HTTPException(403, "You can delete only your comment")
    await db.delete(c); await db.commit()
    return {"ok": True}

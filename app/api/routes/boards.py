from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import timezone
from typing import List
import enum

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.board import Board, BoardStar
from app.models.team import Team, TeamMember, TeamRole
from app.schemas.board import BoardOut, BoardCreate, BoardUpdate

router = APIRouter(prefix="/api/v1/boards", tags=["Boards"])


def _privacy_value(p: object) -> str:
    # radi i ako je Enum i ako je string
    return p.value if isinstance(p, enum.Enum) else str(p)


def _order(sort: str):
    if sort == "title_asc":
        return (Board.title.asc(), Board.updated_at.desc())
    if sort == "title_desc":
        return (Board.title.desc(), Board.updated_at.desc())
    if sort == "activity_asc":
        return (Board.updated_at.asc(),)
    return (Board.updated_at.desc(),)


async def _preview_members(db: AsyncSession, team_id: int | None):
    if not team_id:
        return []
    q = (
        select(TeamMember.user_id, User.display_name, User.avatar_url)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id)
        .order_by(func.random())
        .limit(3)
    )
    rows = (await db.execute(q)).all()
    return [{"id": uid, "name": name or "User", "avatarUrl": avatar} for (uid, name, avatar) in rows]


@router.get("", response_model=List[BoardOut])
async def list_boards(
    q: str | None = Query(None),
    filter: str = Query("all"),                 # all | mine | starred
    sort: str = Query("activity_desc"),         # activity_desc|activity_asc|title_asc|title_desc
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # --- GLOBALNI PRISTUP: važi za sve filtere ---
    memberships = select(TeamMember.team_id).where(TeamMember.user_id == me.id)

    access_predicate = or_(
        (Board.privacy == "public"),   # future-proof
        ((Board.privacy == "team") & (Board.team_id.in_(memberships))),
        ((Board.privacy == "private") & (Board.created_by_id == me.id)),
    )

    stmt = (
        select(Board)
        .options(
            selectinload(Board.stars),
            selectinload(Board.team),
        )
        .where(access_predicate)
        .outerjoin(
            BoardStar,
            (BoardStar.board_id == Board.id) & (BoardStar.user_id == me.id),
        )
    )

    # UI filter
    if filter == "mine":
        stmt = stmt.where(
            or_(
                (Board.created_by_id == me.id),
                (Board.team_id.in_(memberships)),
            )
        )
    elif filter == "starred":
        stmt = stmt.where(BoardStar.user_id == me.id)

    if q:
        stmt = stmt.where(Board.title.ilike(f"%{q}%"))

    for col in _order(sort):
        stmt = stmt.order_by(col)

    res = await db.execute(stmt)
    items = res.scalars().unique().all()

    out: list[BoardOut] = []
    for b in items:
        members = await _preview_members(db, b.team_id)
        is_starred = any(s.user_id == me.id for s in b.stars)
        out.append(
            BoardOut(
                id=b.id,
                title=b.title,
                teamName=b.team.name if b.team_id and b.team else None,
                privacy=_privacy_value(b.privacy),
                isStarred=is_starred,
                lastActivity=(b.updated_at or b.created_at).astimezone(timezone.utc).isoformat(),
                cover=b.cover,
                members=members,
                tags=(b.tags.split(",") if b.tags else []),
                isOwner=(b.created_by_id == me.id),
            )
        )
    return out


@router.post("", response_model=BoardOut, status_code=201)
async def create_board(
    payload: BoardCreate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    if payload.privacy == "team":
        if not payload.team_id:
            raise HTTPException(status_code=422, detail="team_id is required for team visibility")
        # samo OWNER sme da kreira team board
        role = (
            await db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == payload.team_id,
                    TeamMember.user_id == me.id,
                    TeamMember.role == TeamRole.owner,
                )
            )
        ).scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=403, detail="Only team owners can create team boards")

    b = Board(
        title=payload.title.strip(),
        privacy=payload.privacy,  # Enum ili str — ok
        team_id=payload.team_id if payload.privacy == "team" else None,
        created_by_id=me.id,
        tags=",".join(payload.tags) if payload.tags else None,
    )
    db.add(b)
    await db.flush()  # dobijemo b.id

    members = await _preview_members(db, b.team_id)
    result = BoardOut(
        id=b.id,
        title=b.title,
        teamName=(await db.get(Team, b.team_id)).name if b.team_id else None,
        privacy=_privacy_value(b.privacy),
        isStarred=False,
        lastActivity=b.created_at.isoformat(),
        cover=b.cover,
        members=members,
        tags=(b.tags.split(",") if b.tags else []),
        isOwner=True,
    )

    await db.commit()
    return result


@router.patch("/{board_id}/star", status_code=204)
async def toggle_star(
    board_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    existing = (
        await db.execute(
            select(BoardStar).where(
                BoardStar.board_id == board_id,
                BoardStar.user_id == me.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
    else:
        db.add(BoardStar(user_id=me.id, board_id=board_id))

    await db.commit()
    return


@router.patch("/{board_id}", response_model=BoardOut)
async def update_board(
    board_id: int,
    payload: BoardUpdate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    b = await db.get(Board, board_id)
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")

    # samo owner boarda može da menja
    if b.created_by_id != me.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # title
    if payload.title is not None:
        t = payload.title.strip()
        if len(t) < 2:
            raise HTTPException(status_code=422, detail="Title too short")
        b.title = t

    # privacy / team
    if payload.privacy is not None:
        if payload.privacy == "private":
            b.privacy = "private"
            b.team_id = None
        elif payload.privacy == "team":
            team_id = payload.team_id if payload.team_id is not None else b.team_id
            if not team_id:
                raise HTTPException(status_code=422, detail="team_id is required for team visibility")
            # dozvoli promenu samo ako sam OWNER tog tima
            role = (
                await db.execute(
                    select(TeamMember).where(
                        TeamMember.team_id == team_id,
                        TeamMember.user_id == me.id,
                        TeamMember.role == TeamRole.owner,
                    )
                )
            ).scalar_one_or_none()
            if not role:
                raise HTTPException(status_code=403, detail="Only team owners can target team boards")
            b.privacy = "team"
            b.team_id = team_id

    # tags (overwrite)
    if payload.tags is not None:
        b.tags = ",".join(payload.tags) if payload.tags else None

    await db.commit()
    await db.refresh(b)

    members = await _preview_members(db, b.team_id)
    return BoardOut(
        id=b.id,
        title=b.title,
        teamName=(await db.get(Team, b.team_id)).name if b.team_id else None,
        privacy=_privacy_value(b.privacy),
        isStarred=False,  # možeš po želji da vratiš stvarno stanje ako ti treba
        lastActivity=(b.updated_at or b.created_at).astimezone(timezone.utc).isoformat(),
        cover=b.cover,
        members=members,
        tags=(b.tags.split(",") if b.tags else []),
        isOwner=True,
    )


@router.delete("/{board_id}", status_code=204)
async def delete_board(
    board_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    b = await db.get(Board, board_id)
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")

    # samo OWNER (creator) sme da briše
    if b.created_by_id != me.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    await db.delete(b)
    await db.commit()
    return

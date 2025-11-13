from typing import List, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.team import Team, TeamMember, TeamRole
from app.models.invitation import TeamInvite, InviteStatus
from app.models.board import Board  # ⬅️ DODATO: za provere veza sa boardovima
from app.schemas.team import TeamCreate, TeamUpdate, TeamOut, MemberRoleUpdate

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


class InviteIn(BaseModel):
    email: EmailStr


class InviteOut(BaseModel):
    id: int
    team_id: int
    email: EmailStr
    status: InviteStatus


async def _has_team_role(
    db: AsyncSession, team_id: int, user_id: UUID | int, allowed: Set[TeamRole]
) -> bool:
    q = select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    m = (await db.execute(q)).scalar_one_or_none()
    return bool(m and m.role in allowed)


def _safe_notify(db: AsyncSession, recipient_id, kind: str, payload: dict):
    """Never crash the request because of notifications."""
    try:
        from app.models.notification import Notification  # lazy import
        n = Notification(recipient_id=recipient_id, kind=kind, payload=payload)
        db.add(n)
    except Exception:
        pass


@router.get("/me", response_model=List[TeamOut])
async def my_teams(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Team)
        .join(TeamMember)
        .where(TeamMember.user_id == current_user.id, Team.is_archived == False)  # noqa: E712
        .options(selectinload(Team.members).selectinload(TeamMember.user))
    )
    res = await db.execute(q)
    return res.scalars().unique().all()


@router.post("/", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = Team(name=payload.name, description=payload.description)
    try:
        db.add(team)
        await db.flush()
        db.add(TeamMember(team_id=team.id, user_id=current_user.id, role=TeamRole.owner))
        await db.commit()

        team = (
            await db.execute(
                select(Team)
                .where(Team.id == team.id)
                .options(selectinload(Team.members).selectinload(TeamMember.user))
            )
        ).scalars().first()
        return team
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create team")


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Team).where(Team.id == team_id).options(
        selectinload(Team.members).selectinload(TeamMember.user)
    )
    team = (await db.execute(q)).scalars().first()
    if not team:
        raise HTTPException(404, "Team not found")

    m = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.user_id == current_user.id
        )
    )
    if not m.scalar_one_or_none():
        raise HTTPException(403, "Not a team member")

    return team


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(404, "Team not found")

    if not await _has_team_role(db, team_id, current_user.id, {TeamRole.owner}):
        raise HTTPException(403, "Insufficient permissions")

    if payload.name is not None:
        team.name = payload.name
    if payload.description is not None:
        team.description = payload.description
    if payload.is_archived is not None:
        team.is_archived = payload.is_archived

    await db.commit()
    await db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await db.get(Team, team_id)
    if not team:
        raise HTTPException(404, "Team not found")

    if not await _has_team_role(db, team_id, current_user.id, {TeamRole.owner}):
        raise HTTPException(403, "Insufficient permissions")

    # ⬇️ BLOK: ne dozvoli brisanje ako postoje boardovi
    cnt = (await db.execute(
        select(func.count()).select_from(Board).where(Board.team_id == team_id)
    )).scalar_one()
    if cnt and cnt > 0:
        raise HTTPException(
            status_code=409,
            detail="This team cannot be deleted because it still owns one or more boards. Delete or reassign those boards first."
        )

    await db.delete(team)
    await db.commit()
    return None


# === Members ===

@router.patch("/{team_id}/members/{user_id}", response_model=dict)
async def change_member_role(
    team_id: int,
    user_id: UUID,
    payload: MemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await _has_team_role(db, team_id, current_user.id, {TeamRole.owner}):
        raise HTTPException(403, "Insufficient permissions")

    m = (
        await db.execute(
            select(TeamMember).where(
                and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            )
        )
    ).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Member not found")
    if m.role == TeamRole.owner:
        raise HTTPException(400, "Cannot change role of the owner")
    if payload.role not in (TeamRole.developer, TeamRole.manager, TeamRole.owner):
        raise HTTPException(422, "Invalid role")

    team = await db.get(Team, team_id)
    m.role = payload.role

    _safe_notify(
        db,
        recipient_id=user_id,
        kind="team_role_changed",
        payload={
            "team_id": team_id,
            "team_name": team.name if team else "",
            "role": payload.role.value if hasattr(payload.role, "value") else str(payload.role),
        },
    )

    await db.commit()
    return {"ok": True}


@router.delete("/{team_id}/members/{user_id}", response_model=dict)
async def remove_member(
    team_id: int,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    me = current_user.id == user_id
    is_owner = await _has_team_role(db, team_id, current_user.id, {TeamRole.owner})

    m = (
        await db.execute(
            select(TeamMember).where(
                and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
            )
        )
    ).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Member not found")

    team = await db.get(Team, team_id)

    if not me and m.role == TeamRole.owner:
        raise HTTPException(400, "Cannot remove the owner")

    if me:
        if m.role == TeamRole.owner:
            # ⬇️ BLOK: owner ne sme da “leave” ako postoje boardovi
            cnt = (await db.execute(
                select(func.count()).select_from(Board).where(Board.team_id == team_id)
            )).scalar_one()
            if cnt and cnt > 0:
                raise HTTPException(
                    status_code=409,
                    detail="You cannot leave this team because it still owns one or more boards. Transfer or delete those boards first."
                )
            await db.delete(team)
            await db.commit()
            return {"ok": True}

        await db.delete(m)
        rows = (
            await db.execute(
                select(TeamMember.user_id).where(
                    and_(TeamMember.team_id == team_id, TeamMember.user_id != user_id)
                )
            )
        ).scalars().all()
        for rid in rows:
            _safe_notify(
                db,
                recipient_id=rid,
                kind="member_left",
                payload={
                    "team_id": team_id,
                    "team_name": team.name if team else "",
                    "actor_display_name": current_user.display_name or "Member",
                },
            )
        await db.commit()
        return {"ok": True}

    if not is_owner:
        raise HTTPException(403, "Insufficient permissions")

    await db.delete(m)
    _safe_notify(
        db,
        recipient_id=user_id,
        kind="team_kicked",
        payload={"team_id": team_id, "team_name": team.name if team else ""},
    )
    await db.commit()
    return {"ok": True}


# === Invites ===

@router.post("/{team_id}/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    team_id: int,
    body: InviteIn,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # Owner/Manager only
    if not await _has_team_role(db, team_id, me.id, {TeamRole.owner, TeamRole.manager}):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    email = body.email.strip().lower()

    team = await db.scalar(select(Team).where(Team.id == team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    existing = await db.scalar(
        select(TeamInvite)
        .where(TeamInvite.team_id == team_id, func.lower(TeamInvite.email) == email)
        .order_by(TeamInvite.id.desc())
    )

    if existing and existing.status == InviteStatus.pending:
        return InviteOut(
            id=existing.id,
            team_id=existing.team_id,
            email=existing.email,
            status=existing.status,
        )

    if existing:
        await db.execute(
            update(TeamInvite)
            .where(TeamInvite.id == existing.id)
            .values(
                status=InviteStatus.pending,
                invited_by=me.id,
                resolved_at=None,
                created_at=func.now(),
            )
        )
        await db.commit()
        fresh = await db.get(TeamInvite, existing.id)
        return InviteOut(
            id=fresh.id,
            team_id=fresh.team_id,
            email=fresh.email,
            status=fresh.status,
        )

    inv = TeamInvite(
        team_id=team_id,
        email=email,
        invited_by=me.id,
        status=InviteStatus.pending,
    )
    db.add(inv)
    try:
        await db.commit()
        await db.refresh(inv)
    except IntegrityError:
        await db.rollback()
        again = await db.scalar(
            select(TeamInvite)
            .where(TeamInvite.team_id == team_id, func.lower(TeamInvite.email) == email)
            .order_by(TeamInvite.id.desc())
        )
        if again:
            await db.execute(
                update(TeamInvite)
                .where(TeamInvite.id == again.id)
                .values(
                    status=InviteStatus.pending,
                    invited_by=me.id,
                    resolved_at=None,
                    created_at=func.now(),
                )
            )
            await db.commit()
            ref = await db.get(TeamInvite, again.id)
            return InviteOut(id=ref.id, team_id=ref.team_id, email=ref.email, status=ref.status)
        raise HTTPException(status_code=500, detail="Failed to create invite")

    return InviteOut(id=inv.id, team_id=inv.team_id, email=inv.email, status=inv.status)


@router.post("/invites/{invite_id}/accept", response_model=dict)
async def accept_invite(
    invite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = await db.get(TeamInvite, invite_id)
    if not inv or inv.status != InviteStatus.pending:
        raise HTTPException(404, "Invite not found or not pending")

    if inv.email.lower() != current_user.email.lower():
        raise HTTPException(403, "Invite not for this user")

    inv.status = InviteStatus.accepted
    inv.resolved_at = func.now()
    db.add(TeamMember(team_id=inv.team_id, user_id=current_user.id, role=TeamRole.developer))

    team = await db.get(Team, inv.team_id)
    _safe_notify(
        db,
        recipient_id=inv.invited_by,
        kind="invite_accepted",
        payload={
            "team_id": inv.team_id,
            "team_name": team.name if team else "",
            "actor_display_name": current_user.display_name or "Member",
        },
    )
    _safe_notify(
        db,
        recipient_id=current_user.id,
        kind="team_joined",
        payload={"team_id": inv.team_id, "team_name": team.name if team else ""},
    )

    await db.commit()
    return {"ok": True}

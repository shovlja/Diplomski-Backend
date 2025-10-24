from typing import List, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from app.models.invitation import InviteStatus, TeamInvite

from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.team import Team, TeamMember, TeamRole
from app.models.invitation import TeamInvite, InviteStatus
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamOut,
    InviteCreate,
    TeamInviteOut,
    MemberRoleUpdate,
)

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])

class InviteIn(BaseModel):
    email: EmailStr

class InviteOut(BaseModel):
    id: int
    team_id: int
    email: EmailStr
    status: InviteStatus


async def _has_team_role(
    db: AsyncSession, team_id: int, user_id: int, allowed: Set[TeamRole]
) -> bool:
    q = select(TeamMember).where(
        and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    m = (await db.execute(q)).scalar_one_or_none()
    return bool(m and m.role in allowed)


@router.get("/me", response_model=List[TeamOut])
async def my_teams(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Team)
        .join(TeamMember)
        .where(TeamMember.user_id == current_user.id, Team.is_archived == False)
        .options(
            selectinload(Team.members).selectinload(TeamMember.user)  # ⬅️ DODATO
        )
    )
    res = await db.execute(q)
    return res.scalars().unique().all()


@router.post("/", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ukinuli smo unique constraint na name – više timova može imati isto ime
    team = Team(name=payload.name, description=payload.description)
    try:
        db.add(team)
        await db.flush()  # dobijemo team.id

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
    q = (
        select(Team)
        .where(Team.id == team_id)
        .options(
            selectinload(Team.members).selectinload(TeamMember.user)  # ⬅️ DODATO
        )
    )
    team = (await db.execute(q)).scalars().first()
    if not team:
        raise HTTPException(404, "Team not found")

    # dozvola: mora biti član tima
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

    await db.delete(team)
    await db.commit()
    return None


# === Members ===

@router.patch("/{team_id}/members/{user_id}", response_model=dict)
async def change_member_role(
    team_id: int,
    user_id: int,
    payload: MemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # samo owner može menjati uloge – ali ne za owner-a
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

    m.role = payload.role
    await db.commit()
    return {"ok": True}


@router.delete("/{team_id}/members/{user_id}", response_model=dict)
async def remove_member(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # pravila:
    # - owner može ukloniti bilo koga (osim owner-a)
    # - svaki član može ukloniti SAMOG SEBE (leave team)
    # - ako owner ukloni sebe → tim se briše
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

    # zabranjeno: neko drugi pokušava da ukloni owner-a
    if not me and m.role == TeamRole.owner:
        raise HTTPException(400, "Cannot remove the owner")

    if me:
        # vlasnik sam sebe uklanja => brišemo tim
        if m.role == TeamRole.owner:
            team = await db.get(Team, team_id)
            await db.delete(team)
            await db.commit()
            return {"ok": True}
        # ostali mogu sami sebe
        await db.delete(m)
        await db.commit()
        return {"ok": True}

    # ostaje: owner uklanja druge
    if not is_owner:
        raise HTTPException(403, "Insufficient permissions")

    await db.delete(m)
    await db.commit()
    return {"ok": True}


# === Invites ===

@router.post("/{team_id}/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    team_id: int,
    body: InviteIn,
    db: AsyncSession = Depends(get_db),
    me = Depends(get_current_user),
):
    # 1) normalize email
    email = body.email.strip().lower()

    # 2) tim mora da postoji
    team = await db.scalar(select(Team).where(Team.id == team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # 3) ako već postoji pending invite -> vrati ga (idempotentno)
    existing = await db.scalar(
        select(TeamInvite)
        .where(TeamInvite.team_id == team_id, TeamInvite.email == email)
    )
    if existing:
        # možemo i da “oživimo” expired -> pending; ali za sada samo vrati šta postoji
        return InviteOut(id=existing.id, team_id=existing.team_id, email=existing.email, status=existing.status)

    # 4) kreiraj novi invite
    inv = TeamInvite(
        team_id=team_id,
        email=email,
        invited_by=me.id,           # UUID u tvojoj šemi
        status=InviteStatus.pending
    )
    db.add(inv)
    try:
        await db.commit()
        await db.refresh(inv)
    except IntegrityError:
        # ako se neko drugi “utrčao” i kreirao u međuvremenu, idemo idempotentno
        await db.rollback()
        again = await db.scalar(
            select(TeamInvite)
            .where(TeamInvite.team_id == team_id, TeamInvite.email == email)
        )
        if again:
            return InviteOut(id=again.id, team_id=again.team_id, email=again.email, status=again.status)
        # realna greška
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
    inv.resolved_at = datetime.now(timezone.utc)
    db.add(
        TeamMember(team_id=inv.team_id, user_id=current_user.id, role=TeamRole.developer)
    )
    await db.commit()
    return {"ok": True}

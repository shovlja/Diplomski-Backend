# app/api/routes/notifications.py
from typing import List, Literal, TypedDict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.invitation import TeamInvite, InviteStatus
from app.models.team import TeamMember, TeamRole  # koristiš postojeći TeamMember

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# ---- Tipovi koje front očekuje ----
NotificationKind = Literal["team_invite", "team_joined"]

class TeamInvitePayload(TypedDict):
    team_id: int
    team_name: str
    inviter_name: str

class TeamJoinedPayload(TypedDict):
    team_id: int
    team_name: str

class NotificationOut(TypedDict):
    id: int
    kind: NotificationKind
    created_at: str
    is_read: bool
    payload: TeamInvitePayload | TeamJoinedPayload


@router.get("/me", response_model=List[NotificationOut])
async def my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # PENDING -> actionable
    stmt_pending = (
        select(
            TeamInvite.id,
            TeamInvite.team_id,
            Team.name.label("team_name"),
            TeamInvite.created_at.label("ts"),
            User.display_name.label("inviter_name"),
        )
        .join(Team, Team.id == TeamInvite.team_id)
        .join(User, User.id == TeamInvite.invited_by)
        .where(
            TeamInvite.status == InviteStatus.pending,
            TeamInvite.email == current_user.email,
        )
        .order_by(TeamInvite.created_at.desc(), TeamInvite.id.desc())
    )
    pend_rows = (await db.execute(stmt_pending)).all()

    # ACCEPTED -> info "team_joined" (samo All; is_read=True)
    stmt_accepted = (
        select(
            TeamInvite.id,
            TeamInvite.team_id,
            Team.name.label("team_name"),
            TeamInvite.resolved_at.label("ts"),
        )
        .join(Team, Team.id == TeamInvite.team_id)
        .where(
            TeamInvite.status == InviteStatus.accepted,
            TeamInvite.email == current_user.email,
        )
        .order_by(TeamInvite.resolved_at.desc(), TeamInvite.id.desc())
    )
    acc_rows = (await db.execute(stmt_accepted)).all()

    out: List[NotificationOut] = []

    for r in pend_rows:
        out.append(
            {
                "id": r.id,
                "kind": "team_invite",
                "created_at": (r.ts or datetime.now(timezone.utc)).isoformat(),
                "is_read": False,
                "payload": {
                    "team_id": r.team_id,
                    "team_name": r.team_name,
                    "inviter_name": r.inviter_name or "Someone",
                },
            }
        )

    for r in acc_rows:
        out.append(
            {
                "id": r.id,
                "kind": "team_joined",
                "created_at": (r.ts or datetime.now(timezone.utc)).isoformat(),
                "is_read": True,   # ne ulazi u "Unread"
                "payload": {
                    "team_id": r.team_id,
                    "team_name": r.team_name,
                },
            }
        )

    # sort by created_at desc (string ISO je OK, ali bolje prema id/ts)
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


@router.patch("/{notification_id}/accept", response_model=dict)
async def accept_invite_via_notification(
    notification_id: int,  # TeamInvite.id
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = await db.get(TeamInvite, notification_id)
    if not inv or inv.status != InviteStatus.pending:
        raise HTTPException(status_code=404, detail="Invite not found or not pending")
    if inv.email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Invite not for this user")

    inv.status = InviteStatus.accepted
    inv.resolved_at = datetime.now(timezone.utc)

    db.add(TeamMember(team_id=inv.team_id, user_id=current_user.id, role=TeamRole.developer))
    await db.commit()
    return {"ok": True}


@router.patch("/{notification_id}/decline", response_model=dict)
async def decline_invite_via_notification(
    notification_id: int,  # TeamInvite.id
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = await db.get(TeamInvite, notification_id)
    if not inv or inv.status != InviteStatus.pending:
        raise HTTPException(status_code=404, detail="Invite not found or not pending")
    if inv.email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Invite not for this user")

    inv.status = InviteStatus.declined
    inv.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}

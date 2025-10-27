# app/api/routes/notifications.py
from typing import List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.team import Team, TeamMember, TeamRole
from app.models.invitation import TeamInvite, InviteStatus
from app.models.notification import Notification  # ORM tabela

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _iso(dt: datetime | None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


def _safe_notify(db: AsyncSession, recipient_id, kind: str, payload: dict) -> None:
    """Kreiraj notifikaciju, ali nemoj rušiti request ako nešto fali (npr. tabela)."""
    try:
        n = Notification(recipient_id=recipient_id, kind=kind, payload=payload)
        db.add(n)
    except Exception:
        pass


@router.get("/", response_model=List[Dict[str, Any]])
async def list_notifications_raw(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Direktna lista iz notifications tabele (utility)."""
    q = (
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": n.id,
            "kind": n.kind,
            "created_at": _iso(n.created_at),
            "is_read": n.is_read,
            "payload": n.payload or {},
        }
        for n in rows
    ]


@router.get("/me", response_model=List[Dict[str, Any]])
async def my_notifications(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified inbox:
      A) pending invites (actionable)
      B) accepted invites (info 'team_joined')
      C) sve iz notifications tabele (role_changed, kicked, invite_accepted, member_left, …)
    """
    out: List[Dict[str, Any]] = []

    # A) Pending (prikaži pristojno ime pošiljaoca)
    inviter_name_expr = func.coalesce(User.display_name, User.email)

    stmt_pending = (
        select(
            TeamInvite.id,
            TeamInvite.team_id,
            Team.name.label("team_name"),
            TeamInvite.created_at.label("ts"),
            inviter_name_expr.label("inviter_name"),
        )
        .join(Team, Team.id == TeamInvite.team_id)
        .join(User, User.id == TeamInvite.invited_by)
        .where(
            TeamInvite.status == InviteStatus.pending,
            TeamInvite.email == current_user.email,
        )
        .order_by(TeamInvite.created_at.desc(), TeamInvite.id.desc())
    )
    for r in (await db.execute(stmt_pending)).all():
        out.append(
            {
                "id": r.id,
                "kind": "team_invite",
                "created_at": _iso(r.ts),
                "is_read": False,
                "payload": {
                    "team_id": r.team_id,
                    "team_name": r.team_name,
                    "inviter_name": r.inviter_name or "Someone",
                },
            }
        )

    # B) Accepted -> info kartica
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
    for r in (await db.execute(stmt_accepted)).all():
        out.append(
            {
                "id": r.id,
                "kind": "team_joined",
                "created_at": _iso(r.ts),
                "is_read": True,
                "payload": {
                    "team_id": r.team_id,
                    "team_name": r.team_name,
                },
            }
        )

    # C) Sve iz notifications tabele
    stmt_db = (
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    db_rows = (await db.execute(stmt_db)).scalars().all()
    for n in db_rows:
        payload = dict(n.payload or {})
        if n.kind == "team_role_changed":
            if "role" not in payload and "new_role" in payload:
                payload["role"] = payload.get("new_role")
        if n.kind in ("invite_accepted", "member_left"):
            payload.setdefault("actor_display_name", "Member")
            payload.setdefault("actor_avatar_url", None)

        out.append(
            {
                "id": n.id,
                "kind": n.kind,
                "created_at": _iso(n.created_at),
                "is_read": n.is_read,
                "payload": payload,
            }
        )

    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


@router.patch("/{notification_id}/accept", response_model=dict)
async def accept_invite_via_notification(
    notification_id: int,  # TeamInvite.id
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept iz Notifications ekrana.
    Šaljemo:
      - invite_accepted inviteru (sa actor_display_name)
      - team_joined samom korisniku
    """
    inv = await db.get(TeamInvite, notification_id)
    if not inv or inv.status != InviteStatus.pending:
        raise HTTPException(status_code=404, detail="Invite not found or not pending")
    if inv.email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Invite not for this user")

    inv.status = InviteStatus.accepted
    inv.resolved_at = func.now()  # ⬅️ server-side vreme, nema više tz problema

    # membership
    db.add(TeamMember(team_id=inv.team_id, user_id=current_user.id, role=TeamRole.developer))

    # notifikacije
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
    inv.resolved_at = func.now()  # ⬅️ isto ovde
    await db.commit()
    return {"ok": True}

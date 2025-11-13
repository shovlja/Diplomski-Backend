from __future__ import annotations

from typing import Annotated, List
from datetime import date as DateOnly, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.event import Event
from app.schemas.event import EventCreate, EventOut, EventUpdate, CalendarOut

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# 🗓 Upcoming events (Dashboard)
@router.get("/upcoming", response_model=list[EventOut])
async def upcoming_events(
    limit: int = Query(5, ge=1, le=50),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    now = datetime.now(timezone.utc)

    stmt = (
        select(Event)
        .where(
            Event.starts_at >= now,
            Event.owner_id == current_user.id,  # ✅ samo eventovi trenutnog korisnika
        )
        .order_by(Event.starts_at.asc())
        .limit(limit)
    )

    res = await db.execute(stmt)
    return list(res.scalars().all())


# 📅 Calendar highlights (days with events)
@router.get("/calendar", response_model=CalendarOut)
async def calendar_days(
    from_: str = Query(..., alias="from", description="YYYY-MM-DD inclusive"),
    to_: str = Query(..., alias="to", description="YYYY-MM-DD exclusive"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    # Parse inputs
    try:
        fy, fm, fd = map(int, from_.split("-"))
        ty, tm, td = map(int, to_.split("-"))
        start = datetime(fy, fm, fd, tzinfo=timezone.utc)
        end = datetime(ty, tm, td, tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    stmt = (
        select(Event.starts_at)
        .where(
            Event.starts_at >= start,
            Event.starts_at < end,
            Event.owner_id == current_user.id,  # ✅ filtriraj samo korisnikove datume
        )
        .order_by(Event.starts_at.asc())
    )
    res = await db.execute(stmt)
    rows = [r[0] for r in res.all()]

    seen: set[str] = set()
    for dt in rows:
        d = dt.date().isoformat()  # YYYY-MM-DD
        seen.add(d)

    return CalendarOut(dates=sorted(seen))


# 📆 Events for specific day
@router.get("", response_model=List[EventOut])
async def list_events_for_day(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    # Parse YYYY-MM-DD
    try:
        y, m, d = map(int, date.split("-"))
        day = DateOnly(y, m, d)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    # interval [start, end)
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    stmt = (
        select(Event)
        .where(
            Event.starts_at >= start,
            Event.starts_at < end,
            Event.owner_id == current_user.id,  # ✅ prikaz samo mojih eventova
        )
        .order_by(Event.starts_at.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


# ➕ Create event
@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ev = Event(
        title=payload.title,
        starts_at=payload.starts_at,
        owner_id=current_user.id,  # ✅ poveži event sa korisnikom
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


# ✏️ Update event
@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    patch: EventUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ev = await db.get(Event, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if patch.title is not None:
        ev.title = patch.title
    if patch.starts_at is not None:
        ev.starts_at = patch.starts_at

    await db.commit()
    await db.refresh(ev)
    return ev


# 🗑 Delete event
@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    ev = await db.get(Event, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.delete(ev)
    await db.commit()

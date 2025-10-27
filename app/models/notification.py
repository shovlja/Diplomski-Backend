from __future__ import annotations

from datetime import datetime  # ⬅️ bez timezone.utc
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # ⬇️ bitno: koristimo NAIVE UTC (datetime.utcnow), da se poklopi sa TIMESTAMP WITHOUT TIME ZONE
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow()  # NAIVE UTC
    )

    recipient = relationship("User")

from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as pgUUID

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()")
    )

    # 🔹 Dodato: referenca na vlasnika eventa
    owner_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # 🔹 Opcionalno: relationship prema user-u (ako ti zatreba)
    owner = relationship("User", back_populates="events", lazy="joined")

from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class BoardCard(Base):
    __tablename__ = "board_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("board_lists.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text(), default=None)
    position: Mapped[int] = mapped_column(Integer, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    due_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    list = relationship("BoardList", back_populates="cards")
    labels = relationship("CardLabel", back_populates="card", cascade="all, delete-orphan")
    checklists = relationship("BoardChecklist", back_populates="card", cascade="all, delete-orphan")
    comments = relationship("BoardComment", back_populates="card", cascade="all, delete-orphan")
    members = relationship("CardMember", cascade="all, delete-orphan", lazy="selectin")

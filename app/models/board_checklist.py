from __future__ import annotations
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class BoardChecklist(Base):
    __tablename__ = "board_checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("board_cards.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))

    card = relationship("BoardCard", back_populates="checklists")
    items = relationship("BoardChecklistItem", back_populates="checklist", cascade="all, delete-orphan")

class BoardChecklistItem(Base):
    __tablename__ = "board_checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("board_checklists.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(400))
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    checklist = relationship("BoardChecklist", back_populates="items")

from __future__ import annotations
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class BoardLabel(Base):
    __tablename__ = "board_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(7))  # "#RRGGBB"

class CardLabel(Base):
    __tablename__ = "card_labels"

    card_id: Mapped[int] = mapped_column(ForeignKey("board_cards.id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[int] = mapped_column(ForeignKey("board_labels.id", ondelete="CASCADE"), primary_key=True)

    card = relationship("BoardCard", back_populates="labels")
    label = relationship("BoardLabel")

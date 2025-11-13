from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class BoardComment(Base):
    __tablename__ = "board_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("board_cards.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    text: Mapped[str] = mapped_column(Text())

    card = relationship("BoardCard", back_populates="comments")

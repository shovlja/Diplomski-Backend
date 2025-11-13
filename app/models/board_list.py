from __future__ import annotations
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class BoardList(Base):
    __tablename__ = "board_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, index=True)

    
    board = relationship("Board", back_populates="lists")
    cards = relationship(
        "BoardCard",
        back_populates="list",
        cascade="all, delete-orphan",
        order_by="BoardCard.position",
    )

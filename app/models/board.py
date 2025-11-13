# app/models/board.py
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Enum, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import DateTime

from app.db.database import Base

# >>> samo za tipovanje, da ne napravi kružni import u runtime-u
if TYPE_CHECKING:
    from app.models.board_list import BoardList  # noqa: F401


class BoardPrivacy(str, enum.Enum):
    private = "private"
    team = "team"
    public = "public"


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)

    privacy: Mapped[BoardPrivacy] = mapped_column(
        Enum(BoardPrivacy, name="boardprivacy"),
        default=BoardPrivacy.private,
        nullable=False,
    )

    # Pylance više neće prijavljivati “BoardList is not defined”
    lists: Mapped[list["BoardList"]] = relationship(
        "BoardList",
        back_populates="board",
        cascade="all, delete-orphan",
        order_by="BoardList.position",
        lazy="selectin",
    )

    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cover: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    team = relationship("Team", lazy="joined")
    creator = relationship("User", lazy="joined")
    stars = relationship("BoardStar", back_populates="board", cascade="all, delete-orphan")


class BoardStar(Base):
    __tablename__ = "board_stars"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), primary_key=True)

    board = relationship("Board", back_populates="stars")

    __table_args__ = (UniqueConstraint("user_id", "board_id", name="uq_board_star"),)

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
import enum

from sqlalchemy import String, Text, Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# samo za tip-hintove (ne izvršava se u runtime-u, ne pravi ciklus)
if TYPE_CHECKING:
    from app.models.invitation import TeamInvite  # noqa: F401
    from app.models.user import User              # noqa: F401


class TeamRole(str, enum.Enum):
    owner = "owner"
    manager = "manager"
    developer = "developer"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    members: Mapped[List["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    # Bitno: string u relationship + TYPE_CHECKING gore za Pylance
    invites: Mapped[List["TeamInvite"]] = relationship(
        "TeamInvite", back_populates="team", cascade="all, delete-orphan"
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole), default=TeamRole.developer)

    team: Mapped["Team"] = relationship("Team", back_populates="members")
    # String za runtime, TYPE_CHECKING import gore za tip checker
    user: Mapped["User"] = relationship("User")

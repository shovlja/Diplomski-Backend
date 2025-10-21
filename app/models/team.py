from __future__ import annotations
from typing import List, Optional
import enum
from sqlalchemy import String, Text, Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

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
    invites: Mapped[List["TeamInvite"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )

class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole), default=TeamRole.developer)

    team: Mapped[Team] = relationship("Team", back_populates="members")
    from app.models.user import User  # type: ignore  # noqa
    user: Mapped["User"] = relationship("User")

class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"

class TeamInvite(Base):
    __tablename__ = "team_invites"
    __table_args__ = (
        UniqueConstraint("team_id", "email", name="uq_team_email_invite"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), index=True)
    invited_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[InviteStatus] = mapped_column(Enum(InviteStatus), default=InviteStatus.pending)

    team: Mapped[Team] = relationship("Team", back_populates="invites")
    from app.models.user import User  # type: ignore  # noqa
    inviter: Mapped["User"] = relationship("User")

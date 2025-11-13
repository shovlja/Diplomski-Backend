from __future__ import annotations
from datetime import datetime
from enum import Enum
from uuid import UUID as PyUUID, uuid4
from sqlalchemy.dialects.postgresql import UUID as PG_UUID 
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base  # <-- VAŽNO: uvezi Base iz async modula

class SystemRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[PyUUID] = mapped_column(
        PG_UUID(as_uuid=True),           # vraća Python UUID objekte
        primary_key=True,
        default=uuid4,          
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    system_role: Mapped[SystemRole] = mapped_column(SQLEnum(SystemRole), nullable=False, default=SystemRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    events = relationship("Event", back_populates="owner", cascade="all, delete-orphan")
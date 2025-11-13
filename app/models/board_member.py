from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base

class CardMember(Base):
    __tablename__ = "card_members"
    card_id = Column(Integer, ForeignKey("board_cards.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User", lazy="joined")

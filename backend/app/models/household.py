from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.event import Event, household_events

if TYPE_CHECKING:
    from app.models.guest import Guest


class Household(Base):
    """One invitation. Guests look it up with the code printed on their card."""

    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))  # e.g. "The Kim Family"
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")  # en | zh-TW | ko
    max_guests: Mapped[int] = mapped_column(default=1)
    note: Mapped[str | None] = mapped_column(Text)  # message / song request from guests
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    guests: Mapped[list["Guest"]] = relationship(
        back_populates="household", cascade="all, delete-orphan", order_by="Guest.id"
    )
    events: Mapped[list[Event]] = relationship(secondary=household_events, order_by=Event.starts_at)

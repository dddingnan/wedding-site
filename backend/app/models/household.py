from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.event import Event, household_events

if TYPE_CHECKING:
    from app.models.rsvp import Rsvp


class Household(Base):
    """One invitation, answered as a group (no per-person guest list).

    Guests open it with the code (later: link/QR) printed on their card.
    """

    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))  # e.g. "Hsu Family"
    # The person the invitation is addressed to / we contact.
    contact_first_name: Mapped[str | None] = mapped_column(String(100))
    contact_last_name: Mapped[str | None] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")  # en | zh-TW | ko
    # Most people this household may bring (to each event). Admin/manager can change it,
    # but each event's invited households together must stay within that event's capacity.
    max_guests: Mapped[int] = mapped_column(default=1)
    # Main event: sets the invitation's theme. Always also in `events`.
    primary_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT")
    )
    note: Mapped[str | None] = mapped_column(Text)  # message / song request from guests
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    primary_event: Mapped[Event | None] = relationship()
    events: Mapped[list[Event]] = relationship(secondary=household_events, order_by=Event.starts_at)
    # One Rsvp per event this household is invited to.
    rsvps: Mapped[list["Rsvp"]] = relationship(
        back_populates="household", cascade="all, delete-orphan", order_by="Rsvp.event_id"
    )

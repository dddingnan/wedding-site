from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Which households are invited to which events (many-to-many).
# Some guests may only be invited to one of the two ceremonies.
household_events = Table(
    "household_events",
    Base.metadata,
    Column("household_id", ForeignKey("households.id", ondelete="CASCADE"), primary_key=True),
    Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
)


class Event(Base):
    """A ceremony/reception guests RSVP to, or a past one we only remember.

    Display text (title, venue description) lives in the frontend translation
    files keyed by `slug`, so each event reads naturally in en / zh-TW / ko.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)  # e.g. "korea"
    # "upcoming" = guests RSVP to it; "memory" = already happened, read-only (US wedding).
    kind: Mapped[str] = mapped_column(String(16), default="upcoming", server_default="upcoming")
    theme: Mapped[str | None] = mapped_column(String(16))  # invitation colours: gold | red
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))  # IANA, e.g. "Asia/Seoul"
    venue: Mapped[str | None] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(String(500))
    map_url: Mapped[str | None] = mapped_column(String(500))

    hotels: Mapped[list["EventHotel"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by=lambda: [EventHotel.sort_order, EventHotel.id],
    )


class EventHotel(Base):
    """A hotel suggested to guests travelling for an event (the hotel guide)."""

    __tablename__ = "event_hotels"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(String(500))
    map_url: Mapped[str | None] = mapped_column(String(500))
    booking_url: Mapped[str | None] = mapped_column(String(500))
    booking_code: Mapped[str | None] = mapped_column(String(100))  # room-block / group code
    phone: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)  # e.g. "5 min walk", "rate valid until …"
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")

    event: Mapped[Event] = relationship(back_populates="hotels")

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column

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
    """A ceremony/reception guests RSVP to.

    Display text (title, venue description) lives in the frontend translation
    files keyed by `slug`, so each event reads naturally in en / zh-TW / ko.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)  # e.g. "korea"
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))  # IANA, e.g. "Asia/Seoul"
    venue: Mapped[str | None] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(String(500))
    map_url: Mapped[str | None] = mapped_column(String(500))

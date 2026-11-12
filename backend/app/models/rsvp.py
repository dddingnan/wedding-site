from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.guest import Guest


class Rsvp(Base):
    __tablename__ = "rsvps"
    # One answer per guest per event; resubmitting updates the existing row.
    __table_args__ = (UniqueConstraint("guest_id", "event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    attending: Mapped[bool]
    meal: Mapped[str | None] = mapped_column(String(50))
    dietary: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    guest: Mapped["Guest"] = relationship(back_populates="rsvps")

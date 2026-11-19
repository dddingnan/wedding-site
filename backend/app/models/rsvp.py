from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.household import Household


class Rsvp(Base):
    """A household's answer for one event. Resubmitting updates the existing row."""

    __tablename__ = "rsvps"
    __table_args__ = (UniqueConstraint("household_id", "event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    attending: Mapped[bool]
    party_size: Mapped[int] = mapped_column(default=0)  # 0 when not attending
    # How many of each meal, e.g. {"beef": 2, "kids": 1}; adds up to party_size.
    meals: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    # How many people were born in each of the event's gift zodiacs, e.g. {"rat": 1}.
    zodiacs: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    dietary: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    household: Mapped["Household"] = relationship(back_populates="rsvps")

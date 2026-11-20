from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User

if TYPE_CHECKING:
    from app.models.household import Household


class CheckIn(Base):
    """A household arriving at an event. Scanning again updates the same row."""

    __tablename__ = "check_ins"
    __table_args__ = (UniqueConstraint("household_id", "event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    arrived: Mapped[int]  # people who actually came (may differ from the RSVP)
    # Null = the ADMIN_PASSWORD login (no user row) or a deleted helper.
    checked_in_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    household: Mapped["Household"] = relationship(back_populates="check_ins")
    checked_in_by: Mapped[User | None] = relationship()

    @property
    def checked_in_by_name(self) -> str | None:
        return self.checked_in_by.name if self.checked_in_by else None


class Gift(Base):
    """What a household gave at an event, and the zodiac gifts we handed them.

    Admin/manager only: guests can never read this.
    """

    __tablename__ = "gifts"
    __table_args__ = (UniqueConstraint("household_id", "event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    # 禮金, in the event's local currency (KRW in Korea, TWD in Taiwan). One total per
    # household per event; extra envelopes go in `note`.
    amount: Mapped[int] = mapped_column(default=0)
    # Zodiac gifts given, e.g. {"rat": 1}; only the event's gift_zodiacs.
    zodiac_gifts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    note: Mapped[str | None] = mapped_column(String(500))
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    household: Mapped["Household"] = relationship(back_populates="gifts")
    recorded_by: Mapped[User | None] = relationship()

    @property
    def recorded_by_name(self) -> str | None:
        return self.recorded_by.name if self.recorded_by else None

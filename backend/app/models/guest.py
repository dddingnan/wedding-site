from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.rsvp import Rsvp


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(200))
    # Plus-one slots are created blank; the guest fills in the name when RSVPing.
    is_plus_one: Mapped[bool] = mapped_column(default=False)

    household: Mapped["Household"] = relationship(back_populates="guests")
    # One Rsvp per event this guest's household is invited to.
    rsvps: Mapped[list["Rsvp"]] = relationship(
        back_populates="guest", cascade="all, delete-orphan", order_by="Rsvp.event_id"
    )

from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

Role = Literal["admin", "manager"]

# Wrong PINs in a row before a helper account locks. A 6-digit PIN has 1M options,
# so 10 tries (plus the per-IP rate limit) leaves guessing at ~1 in 100,000.
MAX_FAILED_LOGINS = 10


class User(Base):
    """A staff account. Guests never have one (they use their invitation link).

    - admin: the two of us. Will sign in with Google (`google_email`, Phase 5); until
      then the ADMIN_PASSWORD login stands in and has no row here.
    - manager: family helpers on the wedding day. Sign in with `username` + PIN; may
      check households in, record gifts, and change a household's max people.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(16))  # Role
    name: Mapped[str] = mapped_column(String(100))  # shown as "checked in by"
    username: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    pin_hash: Mapped[str | None] = mapped_column(String(200))
    google_email: Mapped[str | None] = mapped_column(String(320), unique=True)
    active: Mapped[bool] = mapped_column(default=True)
    # Wrong PINs in a row; the account locks at MAX_FAILED_LOGINS until an admin resets it.
    failed_logins: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def locked(self) -> bool:
        return self.failed_logins >= MAX_FAILED_LOGINS

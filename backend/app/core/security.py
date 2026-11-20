import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import Role, User

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


# ---------- Passwords / PINs ----------


def verify_admin_password(password: str, settings: Settings) -> bool:
    # compare_digest avoids leaking the password length/prefix through timing.
    return secrets.compare_digest(password.encode(), settings.admin_password.encode())


# scrypt (stdlib) is deliberately slow, so a leaked database doesn't hand out PINs.
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_pin(pin: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str | None) -> bool:
    if not stored:
        return False
    _, salt, digest = stored.split("$")
    actual = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(salt), **_SCRYPT)
    return hmac.compare_digest(actual, bytes.fromhex(digest))


# ---------- Tokens ----------


def _encode(claims: dict, settings: Settings) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({**claims, "exp": expires}, settings.jwt_secret, algorithm=ALGORITHM)


def create_admin_token(settings: Settings) -> str:
    """The ADMIN_PASSWORD login (until Google login): an admin with no user row."""
    return _encode({"sub": "admin", "role": "admin"}, settings)


def create_user_token(user: User, settings: Settings) -> str:
    return _encode({"sub": f"user:{user.id}", "role": user.role}, settings)


@dataclass
class Staff:
    """Whoever is signed in: an admin or a family helper."""

    role: Role
    name: str
    user_id: int | None  # None for the ADMIN_PASSWORD login


def current_staff(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> Staff:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    sub = str(payload.get("sub", ""))
    if sub == "admin":
        return Staff(role="admin", name="admin", user_id=None)
    if sub.startswith("user:") and sub[5:].isdigit():
        # Look the account up every time, so disabling a helper takes effect at once.
        user = db.get(User, int(sub[5:]))
        if user is not None and user.active and not user.locked:
            return Staff(role=user.role, name=user.name, user_id=user.id)  # type: ignore[arg-type]
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer active")


def require_role(*roles: Role):
    def check(staff: Annotated[Staff, Depends(current_staff)]) -> Staff:
        if staff.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
        return staff

    return check


require_admin = require_role("admin")
# Admins can do everything a helper can.
require_staff = require_role("admin", "manager")

StaffDep = Annotated[Staff, Depends(require_staff)]

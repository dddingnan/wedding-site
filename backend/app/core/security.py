import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def verify_admin_password(password: str, settings: Settings) -> bool:
    # compare_digest avoids leaking the password length/prefix through timing.
    return secrets.compare_digest(password.encode(), settings.admin_password.encode())


def create_admin_token(settings: Settings) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": "admin", "exp": expires}, settings.jwt_secret, algorithm=ALGORITHM)


def require_admin(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if payload.get("sub") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an admin")

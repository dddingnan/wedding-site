"""Reusable dependency aliases.

`Annotated[Session, Depends(get_db)]` is FastAPI's recommended style: the type and
the way to obtain it travel together, so route signatures stay short (`db: DbSession`).
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

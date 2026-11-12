import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Household

# No 0/O, 1/I/L: codes are typed in by hand from a printed card,
# often by older relatives, so ambiguous characters cause failed lookups.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6  # 31^6 ≈ 887M combinations; with rate limiting, guessing is impractical.


def normalize(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")


def generate_unique_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        exists = db.scalar(select(Household.id).where(Household.invite_code == code))
        if not exists:
            return code

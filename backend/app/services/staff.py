"""Wedding-day work for helpers (managers) and admins: find a household, check it in,
record gifts."""

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import Staff, hash_pin, verify_pin
from app.models import CheckIn, Event, Gift, Household, User
from app.schemas import CheckInSet, GiftSet
from app.services.rsvp import HOUSEHOLD_LOAD

# Everything a helper/admin sees about a household.
STAFF_LOAD = (
    *HOUSEHOLD_LOAD,
    selectinload(Household.check_ins).selectinload(CheckIn.checked_in_by),
    selectinload(Household.gifts).selectinload(Gift.recorded_by),
)

SEARCH_LIMIT = 20

# Checked when the username doesn't exist, so a wrong username takes as long as a
# wrong PIN (no hint about which usernames are real).
_DUMMY_HASH = hash_pin("000000")


def get_household(db: Session, household_id: int) -> Household:
    household = db.get(Household, household_id, options=STAFF_LOAD, populate_existing=True)
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Household not found")
    return household


def scan(db: Session, token: str) -> Household:
    household_id = db.scalar(select(Household.id).where(Household.invite_token == token.strip()))
    if household_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown QR code")
    return get_household(db, household_id)


def search(db: Session, q: str) -> list[Household]:
    """By household or contact name; every word must match. Only reachable signed in."""
    query = select(Household).order_by(Household.name).limit(SEARCH_LIMIT)
    for word in q.split():
        like = f"%{word}%"
        query = query.where(
            or_(
                Household.name.ilike(like),
                Household.contact_first_name.ilike(like),
                Household.contact_last_name.ilike(like),
            )
        )
    return list(db.scalars(query))


def _invited_event(household: Household, event_id: int) -> Event:
    event = next((e for e in household.events if e.id == event_id), None)
    if event is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"{household.name} is not invited to event {event_id}",
        )
    return event


def set_check_in(
    db: Session, household: Household, event_id: int, body: CheckInSet, staff: Staff
) -> None:
    _invited_event(household, event_id)
    row = next((c for c in household.check_ins if c.event_id == event_id), None)
    if row is None:
        row = CheckIn(event_id=event_id, arrived=body.arrived)
        household.check_ins.append(row)
    row.arrived = body.arrived
    row.checked_in_by_id = staff.user_id
    db.commit()


def clear_check_in(db: Session, household: Household, event_id: int) -> None:
    household.check_ins = [c for c in household.check_ins if c.event_id != event_id]
    db.commit()


def set_gift(db: Session, household: Household, event_id: int, body: GiftSet, staff: Staff) -> None:
    event = _invited_event(household, event_id)
    for animal in body.zodiac_gifts:
        if animal not in event.gift_zodiacs:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"{event.slug}: no {animal} gift"
            )
    row = next((g for g in household.gifts if g.event_id == event_id), None)
    if row is None:
        row = Gift(event_id=event_id)
        household.gifts.append(row)
    row.amount = body.amount
    row.zodiac_gifts = {z: n for z, n in body.zodiac_gifts.items() if n}
    row.note = body.note or None
    row.recorded_by_id = staff.user_id
    db.commit()


def clear_gift(db: Session, household: Household, event_id: int) -> None:
    household.gifts = [g for g in household.gifts if g.event_id != event_id]
    db.commit()


def authenticate(db: Session, username: str, pin: str) -> User:
    """Helper login. Locks the account after too many wrong PINs in a row."""
    wrong = HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or PIN")
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or not user.active or user.pin_hash is None:
        verify_pin(pin, _DUMMY_HASH)
        raise wrong
    if user.locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account locked. Ask an admin to reset it")
    if not verify_pin(pin, user.pin_hash):
        user.failed_logins += 1
        db.commit()
        raise wrong
    if user.failed_logins:
        user.failed_logins = 0
        db.commit()
    return user

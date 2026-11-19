from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Event, Household, Rsvp
from app.schemas import EventResponse, RsvpSubmit
from app.services.invite_codes import normalize

HOUSEHOLD_LOAD = (
    selectinload(Household.rsvps),
    selectinload(Household.events).selectinload(Event.hotels),
)


def get_household_by_code(db: Session, code: str) -> Household:
    household = db.scalar(
        select(Household).where(Household.invite_code == normalize(code)).options(*HOUSEHOLD_LOAD)
    )
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    return household


def _invalid(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def _validate(resp: EventResponse, event: Event, max_guests: int) -> None:
    if not resp.attending:
        return
    if not 1 <= resp.party_size <= max_guests:
        raise _invalid(f"{event.slug}: party size must be between 1 and {max_guests}")
    meals = sum(resp.meals.values())
    if meals != resp.party_size:
        raise _invalid(f"{event.slug}: {meals} meals chosen for {resp.party_size} people")
    for animal, count in resp.zodiacs.items():
        if animal not in event.gift_zodiacs:
            raise _invalid(f"{event.slug}: not asking about {animal}")
        if count > resp.party_size:
            raise _invalid(f"{event.slug}: more {animal} than people coming")


def submit_rsvp(db: Session, code: str, payload: RsvpSubmit) -> Household:
    household = get_household_by_code(db, code)
    events_by_id = {e.id: e for e in household.events}

    for resp in payload.responses:
        event = events_by_id.get(resp.event_id)
        # Reject other event IDs so one code can't answer for an event it isn't invited to.
        if event is None:
            raise _invalid(f"This invitation does not include event {resp.event_id}")
        _validate(resp, event, household.max_guests)

        rsvp = next((r for r in household.rsvps if r.event_id == event.id), None)
        if rsvp is None:
            rsvp = Rsvp(event_id=event.id, attending=resp.attending)
            household.rsvps.append(rsvp)
        rsvp.attending = resp.attending
        # Counts and dietary notes only make sense for people who are coming.
        rsvp.party_size = resp.party_size if resp.attending else 0
        rsvp.meals = {m: n for m, n in resp.meals.items() if n} if resp.attending else {}
        rsvp.zodiacs = {z: n for z, n in resp.zodiacs.items() if n} if resp.attending else {}
        rsvp.dietary = resp.dietary if resp.attending else None

    household.note = payload.note
    household.responded_at = datetime.now(UTC)
    db.commit()
    db.expire_all()
    return get_household_by_code(db, code)

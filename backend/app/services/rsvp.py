from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Event, Guest, Household, Rsvp
from app.schemas import RsvpSubmit
from app.services.invite_codes import normalize

HOUSEHOLD_LOAD = (
    selectinload(Household.guests).selectinload(Guest.rsvps),
    selectinload(Household.events).selectinload(Event.hotels),
)


def get_household_by_code(db: Session, code: str) -> Household:
    household = db.scalar(
        select(Household).where(Household.invite_code == normalize(code)).options(*HOUSEHOLD_LOAD)
    )
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    return household


def submit_rsvp(db: Session, code: str, payload: RsvpSubmit) -> Household:
    household = get_household_by_code(db, code)
    guests_by_id = {g.id: g for g in household.guests}
    invited_event_ids = {e.id for e in household.events}

    for resp in payload.responses:
        guest = guests_by_id.get(resp.guest_id)
        # Reject IDs from other households/events so one code can't edit another invite.
        if guest is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Guest {resp.guest_id} is not on this invitation",
            )
        if resp.event_id not in invited_event_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"This invitation does not include event {resp.event_id}",
            )
        if guest.is_plus_one and resp.full_name:
            guest.full_name = resp.full_name.strip()

        rsvp = next((r for r in guest.rsvps if r.event_id == resp.event_id), None)
        if rsvp is None:
            rsvp = Rsvp(event_id=resp.event_id, attending=resp.attending)
            guest.rsvps.append(rsvp)
        rsvp.attending = resp.attending
        # Meal/dietary only make sense for people who are coming.
        rsvp.meal = resp.meal if resp.attending else None
        rsvp.dietary = resp.dietary if resp.attending else None

    household.note = payload.note
    household.responded_at = datetime.now(UTC)
    db.commit()
    return get_household_by_code(db, code)

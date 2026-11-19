from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Guest, Household
from app.schemas import HouseholdCreate
from app.services.invite_codes import generate_unique_code, normalize


def resolve_events(db: Session, slugs: list[str] | None) -> list[Event]:
    """None means 'every upcoming event'. Unknown slugs are an error, not silently dropped.

    Memory events (already happened) have no RSVP, so nobody can be invited to them.
    """
    upcoming = select(Event).where(Event.kind == "upcoming")
    if slugs is None:
        return list(db.scalars(upcoming))
    events = list(db.scalars(select(Event).where(Event.slug.in_(slugs))))
    missing = set(slugs) - {e.slug for e in events}
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown event(s): {sorted(missing)}"
        )
    memory = sorted(e.slug for e in events if e.kind != "upcoming")
    if memory:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Can't invite to past event(s): {memory}"
        )
    return events


def build_household(db: Session, body: HouseholdCreate) -> Household:
    return Household(
        name=body.name,
        email=body.email,
        preferred_language=body.preferred_language,
        invite_code=normalize(body.invite_code) if body.invite_code else generate_unique_code(db),
        max_guests=len(body.guests),
        guests=[Guest(full_name=g.full_name, is_plus_one=g.is_plus_one) for g in body.guests],
        events=resolve_events(db, body.event_slugs),
    )

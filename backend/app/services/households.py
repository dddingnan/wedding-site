from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event, Household, household_events
from app.schemas import HouseholdCreate, HouseholdUpdate
from app.services.invite_codes import generate_token, generate_unique_code, normalize


def _event_by_slug(db: Session, slug: str) -> Event:
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown event: {slug}")
    if event.kind != "upcoming":
        # Memory events (already happened) have no RSVP, so nobody can be invited to them.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Can't invite to past event: {slug}"
        )
    return event


def resolve_events(db: Session, primary: str, others: list[str]) -> tuple[Event, list[Event]]:
    """Main event + everything the household is invited to (main event included)."""
    main = _event_by_slug(db, primary)
    events = {main.id: main}
    for slug in others:
        event = _event_by_slug(db, slug)
        events[event.id] = event
    return main, list(events.values())


def reserved_seats(db: Session, event_id: int) -> int:
    """Sum of max_guests over the households invited to an event."""
    total = db.scalar(
        select(func.coalesce(func.sum(Household.max_guests), 0))
        .join(household_events, household_events.c.household_id == Household.id)
        .where(household_events.c.event_id == event_id)
    )
    return int(total or 0)


def check_capacity(db: Session, events: list[Event]) -> None:
    """Raise 409 if any event's invited households together exceed its capacity.

    Call after the change is flushed and before commit; the caller's transaction
    is rolled back by the error, so nothing is saved.
    """
    db.flush()
    for event in events:
        if event.capacity is None:
            continue
        reserved = reserved_seats(db, event.id)
        if reserved > event.capacity:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{event.slug} would have {reserved} reserved seats, "
                f"over its capacity of {event.capacity}",
            )


def build_household(db: Session, body: HouseholdCreate) -> Household:
    main, events = resolve_events(db, body.primary_event, body.other_events)
    household = Household(
        name=body.name.strip(),
        contact_first_name=body.contact_first_name,
        contact_last_name=body.contact_last_name,
        email=body.email,
        preferred_language=body.preferred_language,
        invite_code=normalize(body.invite_code) if body.invite_code else generate_unique_code(db),
        invite_token=generate_token(),
        max_guests=body.max_guests,
        primary_event=main,
        events=events,
    )
    db.add(household)
    check_capacity(db, events)
    return household


def update_household(db: Session, household: Household, body: HouseholdUpdate) -> Household:
    changes = body.model_dump(exclude_unset=True)
    touched = list(household.events)  # events that lose a household only free up seats

    if "max_guests" in changes:
        biggest = max((r.party_size for r in household.rsvps), default=0)
        if changes["max_guests"] < biggest:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"This household already RSVP'd {biggest} people",
            )

    if "primary_event" in changes or "other_events" in changes:
        primary = changes.pop("primary_event", None) or household.primary_event.slug
        if "other_events" in changes:
            others = changes.pop("other_events") or []
        else:
            others = [e.slug for e in household.events]
        main, events = resolve_events(db, primary, others)
        household.primary_event = main
        household.events = events
        # Answers for events they're no longer invited to don't count any more.
        kept = {e.id for e in events}
        household.rsvps = [r for r in household.rsvps if r.event_id in kept]
        touched = events

    for field, value in changes.items():
        setattr(household, field, value)

    check_capacity(db, touched)
    return household

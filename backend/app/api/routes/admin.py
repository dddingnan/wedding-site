import csv
import io
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import DbSession, SettingsDep
from app.core.security import create_admin_token, require_admin, verify_admin_password
from app.models import Event, EventHotel, Household
from app.schemas import (
    AdminLogin,
    EventCreate,
    EventOut,
    EventSummary,
    HouseholdAdminOut,
    HouseholdCreate,
    Summary,
    Token,
)
from app.services.households import build_household
from app.services.rsvp import HOUSEHOLD_LOAD

router = APIRouter(prefix="/admin", tags=["admin"])
protected = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/login", response_model=Token)
def login(body: AdminLogin, settings: SettingsDep):
    if not verify_admin_password(body.password, settings):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password")
    return Token(access_token=create_admin_token(settings))


# ---------- Events ----------


@protected.get("/events", response_model=list[EventOut])
def list_events(db: DbSession):
    return db.scalars(
        select(Event).options(selectinload(Event.hotels)).order_by(Event.starts_at)
    ).all()


@protected.post("/events", response_model=EventOut, status_code=201)
def create_event(body: EventCreate, db: DbSession):
    data = body.model_dump(exclude={"hotels"})
    hotels = [EventHotel(**h.model_dump(), sort_order=i) for i, h in enumerate(body.hotels)]
    event = Event(**data, hotels=hotels)
    db.add(event)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Event slug already exists") from exc
    db.refresh(event)
    return event


# ---------- Households ----------


def _all_households(db: Session) -> list[Household]:
    return list(db.scalars(select(Household).options(*HOUSEHOLD_LOAD).order_by(Household.name)))


@protected.get("/households", response_model=list[HouseholdAdminOut])
def list_households(db: DbSession):
    return _all_households(db)


@protected.post("/households", response_model=HouseholdAdminOut, status_code=201)
def create_household(body: HouseholdCreate, db: DbSession):
    household = build_household(db, body)
    db.add(household)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Invite code already in use") from exc
    db.refresh(household)
    return household


@protected.delete("/households/{household_id}", status_code=204)
def delete_household(household_id: int, db: DbSession):
    household = db.get(Household, household_id)
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    db.delete(household)
    db.commit()


# ---------- Reporting ----------


@protected.get("/summary", response_model=Summary)
def summary(db: DbSession):
    households = _all_households(db)
    # Memory events (e.g. the US wedding) have no RSVPs, so they'd only add zero rows.
    events = db.scalars(
        select(Event).where(Event.kind == "upcoming").order_by(Event.starts_at)
    ).all()

    per_event = []
    for event in events:
        invited = [g for h in households if event in h.events for g in h.guests]
        answers = [r for g in invited for r in g.rsvps if r.event_id == event.id]
        yes = [r for r in answers if r.attending]
        per_event.append(
            EventSummary(
                event_id=event.id,
                slug=event.slug,
                invited=len(invited),
                attending=len(yes),
                declined=len(answers) - len(yes),
                awaiting=len(invited) - len(answers),
                meals=dict(Counter(r.meal or "unspecified" for r in yes)),
            )
        )

    return Summary(
        households=len(households),
        households_responded=sum(1 for h in households if h.responded_at),
        events=per_event,
    )


@protected.get("/export.csv")
def export_csv(db: DbSession):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["event", "household", "invite_code", "language", "guest", "plus_one"]
        + ["attending", "meal", "dietary", "note"]
    )
    for h in _all_households(db):
        for event in h.events:
            for g in h.guests:
                r = next((r for r in g.rsvps if r.event_id == event.id), None)
                writer.writerow(
                    [event.slug, h.name, h.invite_code, h.preferred_language]
                    + [g.full_name, g.is_plus_one]
                    + ["" if r is None else ("yes" if r.attending else "no")]
                    + [r.meal if r else "", r.dietary if r else "", h.note or ""]
                )
    # BOM so Excel opens Chinese/Korean names correctly instead of mojibake.
    content = "﻿" + buf.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="rsvps.csv"'},
    )

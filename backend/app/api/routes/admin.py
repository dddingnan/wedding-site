import csv
import io
from collections import Counter
from typing import get_args

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
    EventAdminOut,
    EventCreate,
    EventSummary,
    EventUpdate,
    HouseholdAdminOut,
    HouseholdCreate,
    HouseholdUpdate,
    Meal,
    Summary,
    Token,
)
from app.services.households import (
    build_household,
    check_capacity,
    reserved_seats,
    update_household,
)
from app.services.rsvp import HOUSEHOLD_LOAD

router = APIRouter(prefix="/admin", tags=["admin"])
protected = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/login", response_model=Token)
def login(body: AdminLogin, settings: SettingsDep):
    if not verify_admin_password(body.password, settings):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password")
    return Token(access_token=create_admin_token(settings))


# ---------- Events ----------


@protected.get("/events", response_model=list[EventAdminOut])
def list_events(db: DbSession):
    return db.scalars(
        select(Event).options(selectinload(Event.hotels)).order_by(Event.starts_at)
    ).all()


@protected.post("/events", response_model=EventAdminOut, status_code=201)
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


@protected.patch("/events/{event_id}", response_model=EventAdminOut)
def update_event(event_id: int, body: EventUpdate, db: DbSession):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "gift_zodiacs" and value is None:
            continue
        setattr(event, field, value)  # capacity: null removes the limit
    check_capacity(db, [event])  # can't shrink below the seats already given out
    db.commit()
    db.refresh(event)
    return event


# ---------- Households ----------


def _all_households(db: Session) -> list[Household]:
    return list(db.scalars(select(Household).options(*HOUSEHOLD_LOAD).order_by(Household.name)))


def _get_household(db: Session, household_id: int) -> Household:
    household = db.get(Household, household_id, options=HOUSEHOLD_LOAD)
    if household is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return household


@protected.get("/households", response_model=list[HouseholdAdminOut])
def list_households(db: DbSession):
    return _all_households(db)


@protected.post("/households", response_model=HouseholdAdminOut, status_code=201)
def create_household(body: HouseholdCreate, db: DbSession):
    try:
        household = build_household(db, body)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Invite code already in use") from exc
    return _get_household(db, household.id)


# TODO(roles): managers will also be allowed to call this (to change max_guests).
@protected.patch("/households/{household_id}", response_model=HouseholdAdminOut)
def edit_household(household_id: int, body: HouseholdUpdate, db: DbSession):
    household = _get_household(db, household_id)
    update_household(db, household, body)
    db.commit()
    db.expire_all()
    return _get_household(db, household_id)


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
        invited = [h for h in households if event in h.events]
        answers = [r for h in invited for r in h.rsvps if r.event_id == event.id]
        yes = [r for r in answers if r.attending]
        meals: Counter[str] = Counter()
        zodiacs: Counter[str] = Counter()
        for r in yes:
            meals.update(r.meals)
            zodiacs.update(r.zodiacs)
        per_event.append(
            EventSummary(
                event_id=event.id,
                slug=event.slug,
                capacity=event.capacity,
                reserved=reserved_seats(db, event.id),
                households_invited=len(invited),
                households_attending=len(yes),
                households_declined=len(answers) - len(yes),
                households_awaiting=len(invited) - len(answers),
                people_attending=sum(r.party_size for r in yes),
                meals=dict(meals),
                zodiacs=dict(zodiacs),
            )
        )

    return Summary(
        households=len(households),
        households_responded=sum(1 for h in households if h.responded_at),
        events=per_event,
    )


@protected.get("/export.csv")
def export_csv(db: DbSession):
    meals = list(get_args(Meal))
    zodiacs = sorted({z for e in db.scalars(select(Event)) for z in e.gift_zodiacs})
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["event", "household", "first_name", "last_name", "invite_code", "language"]
        + ["main_event", "max_guests", "attending", "party_size"]
        + [f"meal_{m}" for m in meals]
        + [f"zodiac_{z}" for z in zodiacs]
        + ["dietary", "note"]
    )
    for h in _all_households(db):
        for event in h.events:
            r = next((r for r in h.rsvps if r.event_id == event.id), None)
            attending = "" if r is None else ("yes" if r.attending else "no")
            writer.writerow(
                [event.slug, h.name, h.contact_first_name or "", h.contact_last_name or ""]
                + [h.invite_code, h.preferred_language]
                + ["yes" if event.id == h.primary_event_id else "", h.max_guests]
                + [attending, r.party_size if r else ""]
                + [r.meals.get(m, 0) if r else "" for m in meals]
                + [r.zodiacs.get(z, 0) if r else "" for z in zodiacs]
                + [(r.dietary or "") if r else "", h.note or ""]
            )
    # BOM so Excel opens Chinese/Korean names correctly instead of mojibake.
    content = "﻿" + buf.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="rsvps.csv"'},
    )

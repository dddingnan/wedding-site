"""Wedding-day API for family helpers (managers). Admins can use it too."""

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import DbSession, SettingsDep
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.security import StaffDep, create_user_token, require_staff
from app.schemas import (
    CheckInSet,
    GiftSet,
    HouseholdUpdate,
    MaxGuestsSet,
    Me,
    ScanBody,
    StaffHouseholdBrief,
    StaffHouseholdOut,
    StaffLogin,
    StaffToken,
)
from app.services import staff as staff_service
from app.services.households import update_household

router = APIRouter(prefix="/staff", tags=["staff"])
protected = APIRouter(prefix="/staff", tags=["staff"], dependencies=[Depends(require_staff)])


@router.post("/login", response_model=StaffToken)
@limiter.limit(lambda: get_settings().staff_login_rate_limit)
def login(request: Request, body: StaffLogin, db: DbSession, settings: SettingsDep):
    user = staff_service.authenticate(db, body.username, body.pin)
    return StaffToken(
        access_token=create_user_token(user, settings),
        role=user.role,  # type: ignore[arg-type]
        name=user.name,
    )


@protected.get("/me", response_model=Me)
def me(staff: StaffDep):
    return Me(role=staff.role, name=staff.name)


# ---------- Finding a household ----------


# POST so the token (a secret) stays out of URLs and logs, like the guest lookup.
@protected.post("/scan", response_model=StaffHouseholdOut)
def scan(body: ScanBody, db: DbSession):
    return staff_service.scan(db, body.token)


@protected.get("/households", response_model=list[StaffHouseholdBrief])
def search(db: DbSession, q: str = Query(min_length=1, max_length=100)):
    return staff_service.search(db, q)


@protected.get("/households/{household_id}", response_model=StaffHouseholdOut)
def get_household(household_id: int, db: DbSession):
    return staff_service.get_household(db, household_id)


# ---------- Changes ----------

HOUSEHOLD = "/households/{household_id}"


@protected.put(HOUSEHOLD + "/check-ins/{event_id}", response_model=StaffHouseholdOut)
def check_in(household_id: int, event_id: int, body: CheckInSet, db: DbSession, staff: StaffDep):
    household = staff_service.get_household(db, household_id)
    staff_service.set_check_in(db, household, event_id, body, staff)
    return staff_service.get_household(db, household_id)


@protected.delete(HOUSEHOLD + "/check-ins/{event_id}", response_model=StaffHouseholdOut)
def undo_check_in(household_id: int, event_id: int, db: DbSession):
    household = staff_service.get_household(db, household_id)
    staff_service.clear_check_in(db, household, event_id)
    return staff_service.get_household(db, household_id)


@protected.put(HOUSEHOLD + "/gifts/{event_id}", response_model=StaffHouseholdOut)
def record_gift(household_id: int, event_id: int, body: GiftSet, db: DbSession, staff: StaffDep):
    household = staff_service.get_household(db, household_id)
    staff_service.set_gift(db, household, event_id, body, staff)
    return staff_service.get_household(db, household_id)


@protected.delete(HOUSEHOLD + "/gifts/{event_id}", response_model=StaffHouseholdOut)
def clear_gift(household_id: int, event_id: int, db: DbSession):
    household = staff_service.get_household(db, household_id)
    staff_service.clear_gift(db, household, event_id)
    return staff_service.get_household(db, household_id)


@protected.put(HOUSEHOLD + "/max-guests", response_model=StaffHouseholdOut)
def set_max_guests(household_id: int, body: MaxGuestsSet, db: DbSession):
    """The one household setting helpers may change (e.g. an extra person turned up).
    Same rules as admin: not below their RSVP, not over the event's capacity."""
    household = staff_service.get_household(db, household_id)
    update_household(db, household, HouseholdUpdate(max_guests=body.max_guests))
    db.commit()
    return staff_service.get_household(db, household_id)

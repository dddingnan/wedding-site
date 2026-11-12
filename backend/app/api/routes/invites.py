from fastapi import APIRouter, Request

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.limiter import limiter
from app.schemas import HouseholdOut, InviteLookup, RsvpSubmit
from app.services import rsvp as rsvp_service

router = APIRouter(prefix="/invites", tags=["invites"])


# POST (not GET /invites/{code}) keeps the code out of URLs, server logs and browser history.
@router.post("/lookup", response_model=HouseholdOut)
@limiter.limit(lambda: get_settings().invite_lookup_rate_limit)
def lookup_invite(request: Request, body: InviteLookup, db: DbSession):
    return rsvp_service.get_household_by_code(db, body.code)


@router.put("/{code}/rsvp", response_model=HouseholdOut)
@limiter.limit(lambda: get_settings().invite_lookup_rate_limit)
def submit_rsvp(request: Request, code: str, body: RsvpSubmit, db: DbSession):
    return rsvp_service.submit_rsvp(db, code, body)

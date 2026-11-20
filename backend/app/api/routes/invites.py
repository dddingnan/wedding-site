from fastapi import APIRouter, Request

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.limiter import limiter
from app.schemas import HouseholdOut, InviteLookup, RsvpSubmit
from app.services import rsvp as rsvp_service

router = APIRouter(prefix="/invites", tags=["invites"])

# The token/code always travels in the JSON body, never the API URL, so it stays out
# of server logs. (The guest's own page URL holds the token; see /invite/[token].)


@router.post("/lookup", response_model=HouseholdOut)
@limiter.limit(lambda: get_settings().invite_lookup_rate_limit)
def lookup_invite(request: Request, body: InviteLookup, db: DbSession):
    return rsvp_service.get_household(db, body)


@router.put("/rsvp", response_model=HouseholdOut)
@limiter.limit(lambda: get_settings().invite_lookup_rate_limit)
def submit_rsvp(request: Request, body: RsvpSubmit, db: DbSession):
    return rsvp_service.submit_rsvp(db, body)

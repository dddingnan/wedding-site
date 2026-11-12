from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Language = Literal["en", "zh-TW", "ko"]
Meal = Literal["beef", "fish", "vegetarian", "kids"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Guest-facing ----------


class InviteLookup(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class EventOut(ORM):
    id: int
    slug: str
    starts_at: datetime
    timezone: str
    venue: str | None
    address: str | None
    map_url: str | None


class RsvpOut(ORM):
    event_id: int
    attending: bool
    meal: Meal | None
    dietary: str | None


class GuestOut(ORM):
    id: int
    full_name: str
    is_plus_one: bool
    rsvps: list[RsvpOut]


class HouseholdOut(ORM):
    name: str
    preferred_language: Language
    note: str | None
    responded_at: datetime | None
    events: list[EventOut]
    guests: list[GuestOut]


class GuestResponse(BaseModel):
    guest_id: int
    event_id: int
    attending: bool
    full_name: str | None = Field(default=None, max_length=200)  # only used for plus-ones
    meal: Meal | None = None
    dietary: str | None = Field(default=None, max_length=500)


class RsvpSubmit(BaseModel):
    responses: list[GuestResponse] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=2000)


# ---------- Admin ----------


class AdminLogin(BaseModel):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EventCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,50}$")
    starts_at: datetime  # include the UTC offset, e.g. 2027-12-26T12:00:00+09:00
    timezone: str = Field(examples=["Asia/Seoul"])
    venue: str | None = None
    address: str | None = None
    map_url: str | None = None


class GuestCreate(BaseModel):
    full_name: str = Field(max_length=200)
    is_plus_one: bool = False


class HouseholdCreate(BaseModel):
    name: str = Field(max_length=200)
    email: str | None = None
    preferred_language: Language = "en"
    guests: list[GuestCreate] = Field(min_length=1)
    invite_code: str | None = Field(default=None, min_length=4, max_length=32)
    # None = invite to every event.
    event_slugs: list[str] | None = None


class HouseholdAdminOut(HouseholdOut):
    id: int
    invite_code: str
    email: str | None
    max_guests: int


class EventSummary(BaseModel):
    event_id: int
    slug: str
    invited: int
    attending: int
    declined: int
    awaiting: int
    meals: dict[str, int]


class Summary(BaseModel):
    households: int
    households_responded: int
    events: list[EventSummary]

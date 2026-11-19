from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Language = Literal["en", "zh-TW", "ko"]
Meal = Literal["beef", "fish", "vegetarian", "kids"]
EventKind = Literal["upcoming", "memory"]
EventTheme = Literal["gold", "red"]
Zodiac = Literal[
    "rat", "ox", "tiger", "rabbit", "dragon", "snake",
    "horse", "goat", "monkey", "rooster", "dog", "pig",
]  # fmt: skip
Count = Annotated[int, Field(ge=0, le=100)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Guest-facing ----------


class InviteLookup(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class HotelOut(ORM):
    name: str
    address: str | None
    map_url: str | None
    booking_url: str | None
    booking_code: str | None
    phone: str | None
    note: str | None


class EventOut(ORM):
    id: int
    slug: str
    kind: EventKind
    theme: EventTheme | None
    starts_at: datetime
    timezone: str
    venue: str | None
    address: str | None
    map_url: str | None
    gift_zodiacs: list[Zodiac]  # the RSVP asks how many people were born in these years
    hotels: list[HotelOut]


class RsvpOut(ORM):
    event_id: int
    attending: bool
    party_size: int
    meals: dict[Meal, int]
    zodiacs: dict[Zodiac, int]
    dietary: str | None


class HouseholdOut(ORM):
    name: str
    contact_first_name: str | None
    contact_last_name: str | None
    preferred_language: Language
    max_guests: int
    primary_event_id: int | None
    note: str | None
    responded_at: datetime | None
    events: list[EventOut]
    rsvps: list[RsvpOut]


class EventResponse(BaseModel):
    """The household's answer for one event."""

    event_id: int
    attending: bool
    party_size: int = Field(default=0, ge=0)  # people coming; ignored when not attending
    meals: dict[Meal, Count] = {}  # must add up to party_size
    zodiacs: dict[Zodiac, Count] = {}  # only the event's gift_zodiacs
    dietary: str | None = Field(default=None, max_length=500)


class RsvpSubmit(BaseModel):
    responses: list[EventResponse] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=2000)


# ---------- Admin ----------


class AdminLogin(BaseModel):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HotelCreate(BaseModel):
    name: str = Field(max_length=300)
    address: str | None = Field(default=None, max_length=500)
    map_url: str | None = Field(default=None, max_length=500)
    booking_url: str | None = Field(default=None, max_length=500)
    booking_code: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    note: str | None = None


class EventCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,50}$")
    kind: EventKind = "upcoming"
    theme: EventTheme | None = None
    starts_at: datetime  # include the UTC offset, e.g. 2027-12-26T12:00:00+09:00
    timezone: str = Field(examples=["Asia/Seoul"])
    venue: str | None = None
    address: str | None = None
    map_url: str | None = None
    capacity: int | None = Field(default=None, ge=1)  # None = no limit yet
    gift_zodiacs: list[Zodiac] = []
    hotels: list[HotelCreate] = []


class EventUpdate(BaseModel):
    """Fields left out are unchanged."""

    capacity: int | None = Field(default=None, ge=1)
    gift_zodiacs: list[Zodiac] | None = None


class EventAdminOut(EventOut):
    capacity: int | None


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)  # e.g. "Hsu Family"
    contact_first_name: str | None = Field(default=None, max_length=100)
    contact_last_name: str | None = Field(default=None, max_length=100)
    email: str | None = None
    preferred_language: Language = "en"
    max_guests: int = Field(default=1, ge=1, le=50)
    primary_event: str  # slug of the main event; sets the invitation theme
    other_events: list[str] = []  # also invited to these (slugs)
    invite_code: str | None = Field(default=None, min_length=4, max_length=32)


class HouseholdUpdate(BaseModel):
    """Fields left out are unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_first_name: str | None = Field(default=None, max_length=100)
    contact_last_name: str | None = Field(default=None, max_length=100)
    email: str | None = None
    preferred_language: Language | None = None
    max_guests: int | None = Field(default=None, ge=1, le=50)
    primary_event: str | None = None
    other_events: list[str] | None = None


class HouseholdAdminOut(HouseholdOut):
    id: int
    invite_code: str
    email: str | None


class EventSummary(BaseModel):
    event_id: int
    slug: str
    capacity: int | None
    reserved: int  # sum of max_guests of invited households (must stay <= capacity)
    households_invited: int
    households_attending: int
    households_declined: int
    households_awaiting: int
    people_attending: int
    meals: dict[str, int]
    zodiacs: dict[str, int]


class Summary(BaseModel):
    households: int
    households_responded: int
    events: list[EventSummary]

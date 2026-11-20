from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.config import get_settings

Language = Literal["en", "zh-TW", "ko"]
Meal = Literal["beef", "fish", "vegetarian", "kids"]
EventKind = Literal["upcoming", "memory"]
EventTheme = Literal["gold", "red"]
Zodiac = Literal[
    "rat", "ox", "tiger", "rabbit", "dragon", "snake",
    "horse", "goat", "monkey", "rooster", "dog", "pig",
]  # fmt: skip
Count = Annotated[int, Field(ge=0, le=100)]
Role = Literal["admin", "manager"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Guest-facing ----------


class InviteCredential(BaseModel):
    """Identifies a household: the token from the invitation link/QR, or the typed code.

    Sent in the request body (never the URL) so it stays out of server logs.
    """

    token: str | None = Field(default=None, min_length=16, max_length=64)
    code: str | None = Field(default=None, min_length=4, max_length=32)

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.token is None) == (self.code is None):
            raise ValueError("Send either token or code")
        return self


class InviteLookup(InviteCredential):
    pass


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


class RsvpSubmit(InviteCredential):
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


# ---------- Wedding day (admin + manager) ----------


class CheckInOut(ORM):
    event_id: int
    arrived: int
    checked_in_at: datetime
    checked_in_by_name: str | None  # None = admin password login


class GiftOut(ORM):
    event_id: int
    amount: int  # in the event's local currency (KRW / TWD)
    zodiac_gifts: dict[Zodiac, int]
    note: str | None
    updated_at: datetime
    recorded_by_name: str | None


class StaffHouseholdOut(HouseholdOut):
    """What a helper sees after scanning a QR or searching: RSVP + wedding-day records."""

    id: int
    check_ins: list[CheckInOut]
    gifts: list[GiftOut]


class StaffHouseholdBrief(ORM):
    """Search result row; open the household for the rest."""

    id: int
    name: str
    contact_first_name: str | None
    contact_last_name: str | None


class ScanBody(BaseModel):
    token: str = Field(min_length=16, max_length=64)  # from the household's QR


class CheckInSet(BaseModel):
    arrived: int = Field(ge=1, le=50)  # undo a check-in with DELETE instead of 0


class GiftSet(BaseModel):
    amount: int = Field(default=0, ge=0, le=1_000_000_000)
    zodiac_gifts: dict[Zodiac, Count] = {}  # only the event's gift_zodiacs
    note: str | None = Field(default=None, max_length=500)


class MaxGuestsSet(BaseModel):
    max_guests: int = Field(ge=1, le=50)


class StaffLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    pin: str = Field(min_length=1, max_length=20)


class StaffToken(Token):
    role: Role
    name: str


class Me(BaseModel):
    role: Role
    name: str


# ---------- Admin: helper accounts ----------

Pin = Annotated[str, Field(pattern=r"^\d{6,8}$", examples=["482913"])]  # 6-8 digits


class UserCreate(BaseModel):
    """A family helper (manager). Admins will sign in with Google instead."""

    name: str = Field(min_length=1, max_length=100)  # e.g. "Uncle Wei"
    username: str = Field(pattern=r"^[A-Za-z0-9._-]{2,50}$")
    pin: Pin


class UserUpdate(BaseModel):
    """Fields left out are unchanged. Setting a new PIN also unlocks the account."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    pin: Pin | None = None
    active: bool | None = None


class UserOut(ORM):
    id: int
    role: Role
    name: str
    username: str | None
    active: bool
    locked: bool
    created_at: datetime


class HouseholdAdminOut(StaffHouseholdOut):
    invite_code: str
    invite_token: str
    email: str | None

    @computed_field
    @property
    def invite_url(self) -> str:
        """Full link for the card/QR, built from SITE_URL."""
        return get_settings().invite_url(self.invite_token)


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
    # Wedding day
    households_checked_in: int
    people_arrived: int
    gift_total: int  # event's local currency
    zodiac_gifts_given: dict[str, int]


class Summary(BaseModel):
    households: int
    households_responded: int
    events: list[EventSummary]

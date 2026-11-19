"""Create (or update) the wedding events. Safe to re-run.

Usage (from backend/):
    uv run python -m scripts.seed_events

Edit EVENTS below when venues/times are confirmed. Titles and descriptions
shown to guests live in frontend/messages/*.json under "events.<slug>".
Keep frontend/src/lib/schedule.ts in sync (home page).

`hotels` is the hotel guide for that event. Re-running replaces the event's
hotel list with the one below.
"""

from datetime import datetime
from urllib.parse import quote_plus

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Event, EventHotel


def google_maps_url(query: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


KOREA_VENUE = "The Westin Josun Seoul"
KOREA_ADDRESS = "106 Sogong-ro, Jung District, Seoul, South Korea"
TAIWAN_VENUE = "Mandarin Oriental, Taipei"
TAIWAN_ADDRESS = "No. 158, Dunhua N. Rd., Songshan District, Taipei City, Taiwan 10548"
US_VENUE = "Circuit Court for Baltimore County"
US_ADDRESS = "401 Bosley Ave, Towson, MD 21204"

EVENTS = [
    {
        "slug": "korea",
        "kind": "upcoming",
        "theme": "gold",
        # TODO: confirm ceremony time. Keep the UTC offset in the timestamp.
        "starts_at": datetime.fromisoformat("2027-12-26T12:00:00+09:00"),
        "timezone": "Asia/Seoul",
        "venue": KOREA_VENUE,
        "address": KOREA_ADDRESS,
        "map_url": google_maps_url(f"{KOREA_VENUE}, {KOREA_ADDRESS}"),
        "hotels": [],  # TODO: hotel guide (room block / booking code?)
    },
    {
        "slug": "taiwan",
        "kind": "upcoming",
        "theme": "red",
        "starts_at": datetime.fromisoformat("2028-01-02T12:00:00+08:00"),
        "timezone": "Asia/Taipei",
        "venue": TAIWAN_VENUE,
        "address": TAIWAN_ADDRESS,
        "map_url": google_maps_url(f"{TAIWAN_VENUE}, {TAIWAN_ADDRESS}"),
        "hotels": [],  # TODO: hotel guide (room block / booking code?)
    },
    {
        # Already happened: memory page only, no RSVP.
        "slug": "us",
        "kind": "memory",
        "theme": None,
        # Noon local time (EDT).
        "starts_at": datetime.fromisoformat("2025-04-11T12:00:00-04:00"),
        "timezone": "America/New_York",
        "venue": US_VENUE,
        "address": US_ADDRESS,
        "map_url": google_maps_url(f"{US_VENUE}, {US_ADDRESS}"),
        "hotels": [],
    },
]


def main() -> None:
    with SessionLocal() as db:
        for data in EVENTS:
            fields = {k: v for k, v in data.items() if k != "hotels"}
            hotels = [EventHotel(**h, sort_order=i) for i, h in enumerate(data["hotels"])]
            event = db.scalar(select(Event).where(Event.slug == data["slug"]))
            if event is None:
                db.add(Event(**fields, hotels=hotels))
                print(f"created  {data['slug']}")
            else:
                for key, value in fields.items():
                    setattr(event, key, value)
                event.hotels = hotels
                print(f"updated  {data['slug']}")
        db.commit()


if __name__ == "__main__":
    main()

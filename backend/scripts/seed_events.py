"""Create (or update) the wedding events. Safe to re-run.

Usage (from backend/):
    uv run python -m scripts.seed_events

Edit EVENTS below when venues/times are confirmed. Titles and descriptions
shown to guests live in frontend/messages/*.json under "events.<slug>".
"""

from datetime import datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Event

EVENTS = [
    {
        "slug": "korea",
        # TODO: confirm ceremony time. Keep the UTC offset in the timestamp.
        "starts_at": datetime.fromisoformat("2027-12-26T12:00:00+09:00"),
        "timezone": "Asia/Seoul",
        "venue": None,
        "address": None,
        "map_url": None,
    },
    {
        "slug": "second",
        # TODO: set the real location's offset/timezone (noon local time).
        "starts_at": datetime.fromisoformat("2028-01-02T12:00:00-05:00"),
        "timezone": "America/New_York",
        "venue": None,
        "address": None,
        "map_url": None,
    },
]


def main() -> None:
    with SessionLocal() as db:
        for data in EVENTS:
            event = db.scalar(select(Event).where(Event.slug == data["slug"]))
            if event is None:
                db.add(Event(**data))
                print(f"created  {data['slug']}")
            else:
                for key, value in data.items():
                    setattr(event, key, value)
                print(f"updated  {data['slug']}")
        db.commit()


if __name__ == "__main__":
    main()

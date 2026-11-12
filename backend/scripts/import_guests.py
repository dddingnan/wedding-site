"""Bulk-create invitations from a CSV.

Usage (from backend/):
    uv run python -m scripts.import_guests guests.csv

Create the events first (admin API: POST /api/admin/events, or scripts.seed_events).

CSV columns (header row required):
    household,email,language,guests,plus_ones,events,invite_code

    household   "The Kim Family"
    email       optional
    language    en | zh-TW | ko   (default en)
    guests      names separated by ";"   e.g. "Minji Kim;Jisoo Kim"
    plus_ones   number of blank plus-one slots (default 0)
    events      event slugs separated by ";"   blank = all events
    invite_code optional; generated when blank

Prints each household with its invite code so you can print the cards.
"""

import csv
import sys

from app.db.session import SessionLocal
from app.schemas import GuestCreate, HouseholdCreate
from app.services.households import build_household


def _split(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def main(path: str) -> None:
    with open(path, newline="", encoding="utf-8-sig") as f, SessionLocal() as db:
        for row in csv.DictReader(f):
            plus_ones = int(row.get("plus_ones") or 0)
            body = HouseholdCreate(
                name=row["household"].strip(),
                email=(row.get("email") or "").strip() or None,
                preferred_language=(row.get("language") or "en").strip(),
                guests=[GuestCreate(full_name=n) for n in _split(row["guests"])]
                + [GuestCreate(full_name="Guest", is_plus_one=True) for _ in range(plus_ones)],
                event_slugs=_split(row.get("events")) or None,
                invite_code=(row.get("invite_code") or "").strip() or None,
            )
            household = build_household(db, body)
            db.add(household)
            db.flush()  # so the next generated code sees this one
            slugs = ",".join(e.slug for e in household.events)
            print(
                f"{household.invite_code}  {household.name}  ({len(body.guests)} guests; {slugs})"
            )
        db.commit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

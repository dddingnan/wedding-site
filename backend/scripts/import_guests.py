"""Bulk-create invitations from a CSV.

Usage (from backend/):
    uv run python -m scripts.import_guests guests.csv

Create the events first (scripts.seed_events).

CSV columns (header row required):
    household,first_name,last_name,email,language,max_guests,main_event,other_events,invite_code

    household     "Hsu Family"
    first_name    contact person, optional
    last_name     contact person, optional
    email         optional
    language      en | zh-TW | ko   (default en)
    max_guests    most people this household may bring (default 1)
    main_event    event slug, e.g. korea; sets the invitation theme
    other_events  more event slugs separated by ";", optional
    invite_code   optional; generated when blank

All rows are saved together or not at all (e.g. if an event would go over capacity).
Prints each household with its invite code so you can print the cards.
"""

import csv
import sys

from fastapi import HTTPException

from app.db.session import SessionLocal
from app.schemas import HouseholdCreate
from app.services.households import build_household


def _split(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def _text(row: dict[str, str], column: str) -> str | None:
    return (row.get(column) or "").strip() or None


def main(path: str) -> None:
    with open(path, newline="", encoding="utf-8-sig") as f, SessionLocal() as db:
        for line, row in enumerate(csv.DictReader(f), start=2):
            body = HouseholdCreate(
                name=row["household"].strip(),
                contact_first_name=_text(row, "first_name"),
                contact_last_name=_text(row, "last_name"),
                email=_text(row, "email"),
                preferred_language=_text(row, "language") or "en",
                max_guests=int(_text(row, "max_guests") or 1),
                primary_event=row["main_event"].strip(),
                other_events=_split(row.get("other_events")),
                invite_code=_text(row, "invite_code"),
            )
            try:
                household = build_household(db, body)  # flushes, so the next code is unique
            except HTTPException as exc:
                sys.exit(f"line {line} ({body.name}): {exc.detail}. Nothing was imported.")
            slugs = ",".join(e.slug for e in household.events)
            print(f"{household.invite_code}  {household.name}  (max {body.max_guests}; {slugs})")
        db.commit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

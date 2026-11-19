# Wedding Site — TODO

## Decisions made

| Topic | Decision |
|---|---|
| Ceremonies | **Korea** (Westin) — 2027-12-26 · **Taiwan** (Mandarin Oriental) — 2028-01-02, noon |
| US wedding | Already happened → **memory page** (photos, story), not an RSVP event |
| Finding an invitation | **QR code / household link only.** No name search. If a guest loses it, they contact us, or a helper looks them up on the day |
| Invitation unit | **Household only.** One QR per household, also used for check-in (helper enters how many arrived). Named by household (e.g. Hsu Family) + a contact first/last name; no per-person guest list. A solo guest = household of one |
| Household size | Each household has a **max people**; admin and manager can change it. Per event, the invited households' max people can't add up to more than the event's **capacity** |
| Events per household | One **main event** (sets the invitation theme); optionally also invited to the other one |
| RSVP answers | Per household, per event: coming yes/no, how many people, **meal counts** (beef / fish / vegetarian / kids, must add up to the party size; menu still open), zodiac counts, allergies |
| Zodiac gifts | No birth year. Ask how many people were born in the event's gift animals: **Korea = rooster, rat** · **Taiwan = dragon, rat**. Icons: our own cute art (no Pokémon), emoji placeholders for now |
| Language | Browser language first (`ko`, `zh-*`); otherwise by country (KR → 한국어, TW → 繁體中文); everyone else → English |
| Check-in staff | **Family helpers** → need a "manager" role, separate from admin |
| Admin login | Google login, allowlist of our two accounts |
| Photos | Start in `frontend/public/` (Vercel CDN, free); move to Cloudflare R2 only if the gallery gets big. Not S3 |

## Open questions

- [x] Venues: Korea = The Westin Josun Seoul · Taiwan = Mandarin Oriental, Taipei (2028-01-02, noon)
- [ ] Korea ceremony: exact time (seeded as 12:00 placeholder)
- [ ] Hotel guide: which hotels per event, room block / booking code?
- [x] US wedding: 2025-04-11, Circuit Court for Baltimore County (Towson courthouse)
- [ ] US wedding: which photos/story to include
- [ ] RSVP deadline
- [ ] Our names in 中文 / 한국어 for each language version
- [x] Which zodiacs get a special gift: Korea = rooster, rat · Taiwan = dragon, rat
- [ ] What the zodiac gift is
- [ ] Capacity of each venue (max people)
- [ ] Meal options: keep beef / fish / vegetarian / kids, or does the venue serve a set menu?
- [ ] Email invites/confirmations: yes or no? (needs guest emails + an email provider)

---

## Phase 1 — Data model (do first; everything depends on it)

- [x] Fix event data: Taiwan time zone `Asia/Taipei` (currently a `America/New_York` placeholder), venue name/address/map link for each
- [x] Event `theme`: Korea = gold, Taiwan = red
- [x] Event `kind`: `upcoming` (RSVP) vs `memory` (US wedding, read-only)
- [x] Household: replace fixed plus-one slots with a **max people** set by admin/manager, capped by event **capacity**
- [x] Household: contact first/last name; **main event** + optional other event
- [x] RSVP per household per event: party size, meal counts, zodiac counts (no per-person guests)
- [ ] Household: **long token** for the invitation link/QR (keep the short 6-char code as a typed fallback)
- [x] Zodiac: event `gift_zodiacs`; RSVP asks how many people per gift animal (no birth year)
- [ ] `Table` model + seat assignment per household, per event
- [x] Hotel/travel info per event (hotel guide)
- [ ] Check-in record: household, event, how many arrived, time, checked in by (helper)
- [ ] Gift record: amount (禮金), zodiac gifts given (how many) — **admin/manager only**
- [ ] Roles: `admin`, `manager`
- [x] Alembic migration + tests (events, households/RSVP)
- [ ] Alembic migration + tests (tables, check-in, gifts, roles)

## Phase 2 — Invite flow

- [ ] Generate household link + QR code from admin page (printable / downloadable for the paper invitation)
- [ ] Link opens straight into that household's invitation — no typing
- [ ] Remove the public invite-code-only entry; keep a small "have a code?" fallback
- [ ] Public home page shows **no private event details**; details only after the link identifies the guest

## Phase 3 — Guest experience

- [ ] **Envelope / card animation:** closed card shows the household name → pull the ribbon → card opens to details + RSVP, this should be in different path like /invite or.
  - [ ] "Tap to open" fallback; respect reduce-motion setting
- [ ] Theme per invitation (gold / red) based on the event they're invited to
- [ ] Venue icon: hotel name + original line-art icon or a photo we're allowed to use (no hotel logos)
- [ ] RSVP steps, one question per screen:
  - [ ] How many are coming (up to the household max)
  - [ ] Meals for each person (counts)
  - [ ] Zodiac animals (only the event's gift animals; own icons)
- [ ] Details page after RSVP: date/time, venue + map, **table number**, hotel guide
- [ ] "Add to calendar" (`.ics` download)
- [ ] Optional: confirmation email (pending decision)
- [ ] Language detection rule from Decisions table
- [ ] **All ages & devices pass:** larger text, high contrast, big tap targets, simple wording, test on older phones, contact phone number visible

## Phase 4 — Memory page (US wedding)

- [ ] Public (or link-only?) page: story, date, place, photo gallery
- [ ] Optimized images; lazy loading
- [ ] Designed to last years — no dependence on RSVP data

## Phase 5 — Admin (our own path, outside language routes)

- [ ] Google login, allowlisted to our two accounts; backend verifies the Google token
- [x] Set max people per household (basic: number field in the invitations table)
- [ ] Seating: create tables, assign households per event
- [ ] Generate / reprint QR codes
- [ ] Manage helper (manager) accounts
- [ ] Headcount, meals, zodiac gift list per event; CSV export

## Phase 6 — Manager flow (day of the wedding, family helpers)

- [ ] Simple helper login (limited access: check-in, gifts, change a household's max people)
- [ ] Check-in way 1: scan the household QR → enter how many arrived → done
- [ ] Check-in way 2: helper searches the household by name and checks them in (search only inside the helper screen, never public)
- [ ] Show table number on check-in so the helper can direct them
- [ ] Flag households with zodiac guests → mark gifts given
- [ ] Record gift money amount
- [ ] Works on mobile data (venue Wi-Fi may be bad); keep a printed backup list
- [ ] Gift data included in DB backups
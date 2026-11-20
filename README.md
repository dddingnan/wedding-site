# wedding-site

Wedding invitation site for Dingnan & Hyang — two ceremonies, three languages (English, 繁體中文, 한국어), RSVP by invitation link / QR code.

| Part | Stack |
|---|---|
| `frontend/` | Next.js 16 (App Router, Cache Components), next-intl, Tailwind 4, TypeScript |
| `backend/` | FastAPI, SQLAlchemy 2, Alembic, Pydantic, Postgres |
| Database | Postgres — Docker locally, [Neon](https://neon.com) in production |

## How it works

- Each **household** gets a secret **invitation link** `/invite/<token>` (22 random characters, for the QR code on the card) and a short 6-character **invite code** printed next to it as a typed fallback at `/rsvp` (no look-alike characters like `0/O` or `1/I/L`).
- On the day, family helpers (role `manager`, username + PIN created in admin) scan the same QR or search by name to check households in and record gifts (`/api/staff/*`). Gift data is admin/manager only.
- The same QR is scanned at check-in on the day. If a link leaks, "New link" in admin replaces it (the old one stops working; the code stays).
- Each invitation is a **household** (e.g. Hsu Family) with a max number of people, a main event and optionally the other ceremony.
- Households RSVP **per event**: how many are coming, meal counts, and how many were born in that event's gift zodiac animals.
- Per event, the invited households' max people can't add up to more than the event's capacity.
- `/` redirects to `/en`, `/zh-TW` or `/ko` based on the browser language; the switcher in the header changes it.
- `/en/admin` (password-protected) shows per-event headcounts and meals, lets you add/delete invitations, copy each invitation link, and exports a CSV that opens correctly in Excel with Chinese/Korean names.

## Local development

Prereqs: Docker, Node 22, [uv](https://docs.astral.sh/uv/).

### Everything in Docker

DB, API and a production build of the UI. No hot reload, so this is for trying the whole site, not for editing the frontend.

```bash
cp backend/.env.example backend/.env
docker compose up --build -d        # UI http://localhost:3000, API http://localhost:8000
docker compose exec api python -m scripts.seed_events
docker compose exec api python -m scripts.import_guests scripts/guests.example.csv   # prints invite codes + links
```

After changing frontend code, rebuild with `docker compose up --build -d web`. Stop it all with `docker compose down` (add `-v` to wipe the database).

### Frontend with hot reload

```bash
# 1. Database + API only (runs migrations automatically)
cp backend/.env.example backend/.env
docker compose up --build -d db api

# 2. Seed the two ceremonies and some example guests
cd backend
uv sync
uv run python -m scripts.seed_events
uv run python -m scripts.import_guests scripts/guests.example.csv   # prints invite codes + links

# 3. Frontend
cd ../frontend
cp .env.example .env.local
npm install
npm run dev        # http://localhost:3000
```

API docs (Swagger UI): http://localhost:8000/docs

Without Docker: run Postgres however you like, set `DATABASE_URL` in `backend/.env`, then `uv run alembic upgrade head && uv run fastapi dev app/main.py`.

## Common tasks

| Task | Command |
|---|---|
| Backend tests | `cd backend && uv run pytest` |
| Backend lint/format | `uv run ruff check . && uv run ruff format .` |
| New DB migration after editing models | `uv run alembic revision --autogenerate -m "describe change"` then review the file |
| Regenerate frontend API types after changing the API | `cd frontend && npm run gen:api` |
| Frontend checks | `npm run lint && npm run typecheck && npm run build` |
| Import the real guest list | Fill a CSV like `backend/scripts/guests.example.csv`, then `uv run python -m scripts.import_guests guests.csv` |

## Editing content

- **Text in all three languages**: `frontend/messages/{en,zh-TW,ko}.json`. Keys are type-checked against `en.json`, so a missing key fails the build.
- **Event date/time/venue**: `backend/scripts/seed_events.py` (re-runnable) **and** `frontend/src/lib/schedule.ts` (home page).
- **RSVP deadline**: `RSVP_DEADLINE` in `frontend/src/lib/schedule.ts`.
- **Meal options**: `Meal` in `backend/app/schemas.py`, then `npm run gen:api` and add translations under `meals`.

## Deploying

1. **Neon**: create a project (region near the API host), copy the connection string. A plain `postgresql://…` URL works; the app adds the psycopg driver itself.
2. **API** (Azure Container Apps, Render, Fly.io — anything that runs a Dockerfile): build `backend/`, set env vars `DATABASE_URL`, `ADMIN_PASSWORD`, `JWT_SECRET` (long random string), `CORS_ORIGINS=https://your-domain`, `SITE_URL=https://your-domain` (used in invitation links). Migrations run on startup.
3. **Frontend** (Vercel): root directory `frontend`, env var `NEXT_PUBLIC_API_URL=https://your-api-host`.
4. Run `seed_events` and `import_guests` once against Neon (`DATABASE_URL=… uv run python -m scripts.seed_events`).

## Backups

`.github/workflows/db-backup.yml` runs `pg_dump` every Monday and keeps it for 90 days as a workflow artifact. Add the repo secret **`NEON_DATABASE_URL`** to turn it on. Use **Actions → DB backup → Run workflow** for an on-demand backup. Keep this repo **private**: the backups contain guest data.

Restore: `pg_restore --clean --no-owner -d "$DATABASE_URL" wedding-YYYY-MM-DD.dump`

## Security notes

- Invite lookups are rate-limited per IP (`INVITE_LOOKUP_RATE_LIMIT`, default 10/min) to stop code guessing. The Dockerfile enables `--proxy-headers` so the real client IP is used behind a load balancer.
- Lookups use `POST`, so codes don't end up in server logs or browser history (except the optional QR link).
- A code can only change RSVPs for its own guests and events.
- Admin auth is a single password → short-lived JWT, stored in `sessionStorage`.

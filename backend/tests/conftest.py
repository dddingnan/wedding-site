import os

# Must be set before app modules import settings.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["JWT_SECRET"] = "test-secret-at-least-32-bytes-long!!"
os.environ["INVITE_LOOKUP_RATE_LIMIT"] = "1000/minute"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402, F401  (registers tables on Base.metadata)
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    # StaticPool: one shared in-memory SQLite connection, so every request sees the same data.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(client):
    token = client.post("/api/admin/login", json={"password": "test-password"}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


@pytest.fixture
def events(client, admin_headers):
    """Two ceremonies, like the real wedding."""
    created = []
    for slug, starts_at, tz, theme, zodiacs in [
        ("korea", "2027-12-26T12:00:00+09:00", "Asia/Seoul", "gold", ["rooster", "rat"]),
        ("taiwan", "2028-01-02T12:00:00+08:00", "Asia/Taipei", "red", ["dragon", "rat"]),
    ]:
        res = client.post(
            "/api/admin/events",
            headers=admin_headers,
            json={
                "slug": slug,
                "starts_at": starts_at,
                "timezone": tz,
                "theme": theme,
                "gift_zodiacs": zodiacs,
            },
        )
        assert res.status_code == 201
        created.append(res.json())
    return created


def make_household(client, headers, **fields):
    body = {"name": "Household", "primary_event": "korea", **fields}
    res = client.post("/api/admin/households", headers=headers, json=body)
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def household(client, admin_headers, events):
    """Kim Family: main event Korea, also invited to Taiwan, up to 3 people."""
    return make_household(
        client,
        admin_headers,
        name="Kim Family",
        contact_first_name="Minji",
        contact_last_name="Kim",
        preferred_language="ko",
        max_guests=3,
        primary_event="korea",
        other_events=["taiwan"],
    )

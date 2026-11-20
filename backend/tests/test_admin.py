from tests.conftest import make_household


def test_admin_routes_require_token(client):
    assert client.get("/api/admin/households").status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert client.get("/api/admin/households", headers=bad).status_code == 401


def test_wrong_password(client):
    assert client.post("/api/admin/login", json={"password": "x"}).status_code == 401


def test_generated_code_avoids_ambiguous_chars(household):
    code = household["invite_code"]
    assert len(code) == 6
    assert not set(code) & set("01OIL")


def test_duplicate_custom_code_conflicts(client, admin_headers, events):
    body = {"name": "A", "primary_event": "korea", "invite_code": "LOVE2027"}
    assert client.post("/api/admin/households", headers=admin_headers, json=body).status_code == 201
    assert client.post("/api/admin/households", headers=admin_headers, json=body).status_code == 409


def test_main_event_only_by_default(client, admin_headers, events):
    h = make_household(client, admin_headers, primary_event="taiwan")
    assert h["primary_event_id"] == events[1]["id"]
    assert [e["slug"] for e in h["events"]] == ["taiwan"]


def test_unknown_event_slug_rejected(client, admin_headers, events):
    for body in (
        {"name": "X", "primary_event": "nope"},
        {"name": "X", "primary_event": "korea", "other_events": ["nope"]},
    ):
        res = client.post("/api/admin/households", headers=admin_headers, json=body)
        assert res.status_code == 422


def test_duplicate_event_slug_conflicts(client, admin_headers, events):
    body = {"slug": "korea", "starts_at": "2027-12-26T12:00:00+09:00", "timezone": "Asia/Seoul"}
    assert client.post("/api/admin/events", headers=admin_headers, json=body).status_code == 409


def test_edit_household(client, admin_headers, household, events):
    res = client.patch(
        f"/api/admin/households/{household['id']}",
        headers=admin_headers,
        json={"max_guests": 5, "contact_first_name": "Jisoo", "other_events": []},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["max_guests"] == 5
    assert body["contact_first_name"] == "Jisoo"
    assert [e["slug"] for e in body["events"]] == ["korea"]  # main event always stays


def test_cannot_lower_max_below_rsvp(client, admin_headers, household, events):
    answer = {"event_id": events[0]["id"], "attending": True, "party_size": 3, "meals": {"fish": 3}}
    client.put("/api/invites/rsvp", json={"code": household["invite_code"], "responses": [answer]})
    res = client.patch(
        f"/api/admin/households/{household['id']}", headers=admin_headers, json={"max_guests": 2}
    )
    assert res.status_code == 422


def test_summary_and_export(client, admin_headers, household, events):
    korea = events[0]
    answer = {
        "event_id": korea["id"],
        "attending": True,
        "party_size": 2,
        "meals": {"fish": 1, "kids": 1},
        "zodiacs": {"rat": 1},
    }
    client.put("/api/invites/rsvp", json={"code": household["invite_code"], "responses": [answer]})

    s = client.get("/api/admin/summary", headers=admin_headers).json()
    assert s["households"] == 1
    assert s["households_responded"] == 1
    assert s["events"][0] == {
        "event_id": korea["id"],
        "slug": "korea",
        "capacity": None,
        "reserved": 3,
        "households_invited": 1,
        "households_attending": 1,
        "households_declined": 0,
        "households_awaiting": 0,
        "people_attending": 2,
        "meals": {"fish": 1, "kids": 1},
        "zodiacs": {"rat": 1},
        "households_checked_in": 0,
        "people_arrived": 0,
        "gift_total": 0,
        "zodiac_gifts_given": {},
    }
    assert s["events"][1]["households_awaiting"] == 1

    res = client.get("/api/admin/export.csv", headers=admin_headers)
    assert res.status_code == 200
    lines = res.text.strip().splitlines()
    assert lines[0].startswith("﻿event,household,first_name,last_name,invite_code,invite_url,")
    assert household["invite_url"] in lines[1]
    assert "zodiac_dragon" in lines[0] and "zodiac_rooster" in lines[0]
    assert "Kim Family,Minji,Kim" in res.text
    assert len(lines) == 1 + 2  # header + 1 household x 2 events

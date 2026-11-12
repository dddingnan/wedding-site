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


def test_duplicate_custom_code_conflicts(client, admin_headers):
    body = {"name": "A", "invite_code": "LOVE2027", "guests": [{"full_name": "A"}]}
    assert client.post("/api/admin/households", headers=admin_headers, json=body).status_code == 201
    assert client.post("/api/admin/households", headers=admin_headers, json=body).status_code == 409


def test_summary_and_export(client, admin_headers, household, events):
    gid = household["guests"][0]["id"]
    korea = events[0]
    client.put(
        f"/api/invites/{household['invite_code']}/rsvp",
        json={
            "responses": [
                {"guest_id": gid, "event_id": korea["id"], "attending": True, "meal": "fish"}
            ]
        },
    )

    s = client.get("/api/admin/summary", headers=admin_headers).json()
    assert s["households"] == 1
    assert s["households_responded"] == 1
    assert s["events"][0] == {
        "event_id": korea["id"],
        "slug": "korea",
        "invited": 2,
        "attending": 1,
        "declined": 0,
        "awaiting": 1,
        "meals": {"fish": 1},
    }
    assert s["events"][1]["awaiting"] == 2

    res = client.get("/api/admin/export.csv", headers=admin_headers)
    assert res.status_code == 200
    assert res.text.startswith("\ufeffevent,household,")
    assert "Minji Kim" in res.text
    assert len(res.text.strip().splitlines()) == 1 + 2 * 2  # header + 2 guests x 2 events


def test_unknown_event_slug_rejected(client, admin_headers, events):
    body = {"name": "X", "guests": [{"full_name": "X"}], "event_slugs": ["nope"]}
    assert client.post("/api/admin/households", headers=admin_headers, json=body).status_code == 422


def test_duplicate_event_slug_conflicts(client, admin_headers, events):
    body = {"slug": "korea", "starts_at": "2027-12-26T12:00:00+09:00", "timezone": "Asia/Seoul"}
    assert client.post("/api/admin/events", headers=admin_headers, json=body).status_code == 409

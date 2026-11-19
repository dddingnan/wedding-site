MEMORY = {
    "slug": "us",
    "kind": "memory",
    "starts_at": "2026-06-01T16:00:00-07:00",
    "timezone": "America/Los_Angeles",
}


def test_event_defaults_and_theme(events):
    korea, taiwan = events
    assert korea["kind"] == "upcoming"
    assert (korea["theme"], taiwan["theme"]) == ("gold", "red")
    assert taiwan["timezone"] == "Asia/Taipei"
    assert korea["hotels"] == []


def test_invalid_kind_and_theme_rejected(client, admin_headers):
    base = {"slug": "x1", "starts_at": "2027-12-26T12:00:00+09:00", "timezone": "Asia/Seoul"}
    for extra in ({"kind": "party"}, {"theme": "blue"}):
        res = client.post("/api/admin/events", headers=admin_headers, json={**base, **extra})
        assert res.status_code == 422


def test_hotels_keep_order_and_reach_guests(client, admin_headers):
    res = client.post(
        "/api/admin/events",
        headers=admin_headers,
        json={
            "slug": "korea",
            "starts_at": "2027-12-26T12:00:00+09:00",
            "timezone": "Asia/Seoul",
            "hotels": [
                {"name": "The Westin Josun Seoul", "booking_code": "WED2027"},
                {"name": "Lotte Hotel Seoul", "note": "5 min walk"},
            ],
        },
    )
    assert res.status_code == 201
    assert [h["name"] for h in res.json()["hotels"]] == [
        "The Westin Josun Seoul",
        "Lotte Hotel Seoul",
    ]

    household = client.post(
        "/api/admin/households",
        headers=admin_headers,
        json={"name": "A", "guests": [{"full_name": "A"}]},
    ).json()
    lookup = client.post("/api/invites/lookup", json={"code": household["invite_code"]}).json()
    hotels = lookup["events"][0]["hotels"]
    assert hotels[0]["booking_code"] == "WED2027"
    assert hotels[1]["note"] == "5 min walk"


def test_memory_event_not_invited_by_default(client, admin_headers, events):
    assert client.post("/api/admin/events", headers=admin_headers, json=MEMORY).status_code == 201
    household = client.post(
        "/api/admin/households",
        headers=admin_headers,
        json={"name": "A", "guests": [{"full_name": "A"}]},
    ).json()
    assert [e["slug"] for e in household["events"]] == ["korea", "taiwan"]


def test_cannot_invite_to_memory_event(client, admin_headers, events):
    client.post("/api/admin/events", headers=admin_headers, json=MEMORY)
    body = {"name": "A", "guests": [{"full_name": "A"}], "event_slugs": ["korea", "us"]}
    res = client.post("/api/admin/households", headers=admin_headers, json=body)
    assert res.status_code == 422


def test_summary_skips_memory_events(client, admin_headers, events):
    client.post("/api/admin/events", headers=admin_headers, json=MEMORY)
    s = client.get("/api/admin/summary", headers=admin_headers).json()
    assert [e["slug"] for e in s["events"]] == ["korea", "taiwan"]

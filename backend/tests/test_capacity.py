from tests.conftest import make_household


def set_capacity(client, headers, event, capacity):
    return client.patch(
        f"/api/admin/events/{event['id']}", headers=headers, json={"capacity": capacity}
    )


def test_households_cannot_exceed_event_capacity(client, admin_headers, events):
    assert set_capacity(client, admin_headers, events[0], 5).status_code == 200
    make_household(client, admin_headers, name="A", max_guests=3)
    res = client.post(
        "/api/admin/households",
        headers=admin_headers,
        json={"name": "B", "primary_event": "korea", "max_guests": 3},
    )
    assert res.status_code == 409
    assert "capacity of 5" in res.json()["detail"]
    # The rejected household wasn't saved.
    names = [h["name"] for h in client.get("/api/admin/households", headers=admin_headers).json()]
    assert names == ["A"]
    make_household(client, admin_headers, name="B", max_guests=2)  # exactly full is fine


def test_raising_max_guests_is_capped(client, admin_headers, events):
    set_capacity(client, admin_headers, events[0], 4)
    a = make_household(client, admin_headers, name="A", max_guests=2)
    make_household(client, admin_headers, name="B", max_guests=2)
    url = f"/api/admin/households/{a['id']}"
    assert client.patch(url, headers=admin_headers, json={"max_guests": 3}).status_code == 409
    households = client.get("/api/admin/households", headers=admin_headers).json()
    assert households[0]["max_guests"] == 2


def test_adding_an_event_checks_its_capacity(client, admin_headers, events):
    set_capacity(client, admin_headers, events[1], 2)
    a = make_household(client, admin_headers, name="A", max_guests=3)  # korea only
    res = client.patch(
        f"/api/admin/households/{a['id']}", headers=admin_headers, json={"other_events": ["taiwan"]}
    )
    assert res.status_code == 409


def test_cannot_shrink_capacity_below_reserved(client, admin_headers, events):
    korea = events[0]
    make_household(client, admin_headers, name="A", max_guests=3)
    assert set_capacity(client, admin_headers, korea, 2).status_code == 409
    assert set_capacity(client, admin_headers, korea, 3).status_code == 200
    assert set_capacity(client, admin_headers, korea, None).json()["capacity"] is None

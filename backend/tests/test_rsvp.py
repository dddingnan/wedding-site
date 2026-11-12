def test_lookup_is_case_and_dash_insensitive(client, household):
    code = household["invite_code"]
    messy = f" {code[:3].lower()}-{code[3:].lower()} "
    res = client.post("/api/invites/lookup", json={"code": messy})
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "The Kim Family"
    assert body["preferred_language"] == "ko"
    assert [e["slug"] for e in body["events"]] == ["korea", "second"]  # sorted by date
    assert "invite_code" not in body  # guests never see admin fields


def test_unknown_code_returns_404(client):
    res = client.post("/api/invites/lookup", json={"code": "ZZZZZZ"})
    assert res.status_code == 404


def test_rsvp_per_event_and_plus_one_name(client, household, events):
    code = household["invite_code"]
    main, plus_one = household["guests"]
    korea, second = events
    res = client.put(
        f"/api/invites/{code}/rsvp",
        json={
            "responses": [
                {
                    "guest_id": main["id"],
                    "event_id": korea["id"],
                    "attending": True,
                    "meal": "fish",
                },
                {"guest_id": main["id"], "event_id": second["id"], "attending": False},
                {
                    "guest_id": plus_one["id"],
                    "event_id": korea["id"],
                    "attending": True,
                    "full_name": "Jun Park",
                    "meal": "beef",
                    "dietary": "no shellfish",
                },
            ],
            "note": "Can't wait!",
        },
    )
    assert res.status_code == 200
    guests = res.json()["guests"]
    assert guests[1]["full_name"] == "Jun Park"
    assert {(r["event_id"], r["attending"]) for r in guests[0]["rsvps"]} == {
        (korea["id"], True),
        (second["id"], False),
    }
    assert res.json()["responded_at"] is not None


def test_resubmit_updates_and_declining_clears_meal(client, household, events):
    code = household["invite_code"]
    gid, eid = household["guests"][0]["id"], events[0]["id"]
    first = {"guest_id": gid, "event_id": eid, "attending": True, "meal": "fish"}
    client.put(f"/api/invites/{code}/rsvp", json={"responses": [first]})
    res = client.put(
        f"/api/invites/{code}/rsvp",
        json={"responses": [{**first, "attending": False}]},
    )
    rsvps = res.json()["guests"][0]["rsvps"]
    assert rsvps == [{"event_id": eid, "attending": False, "meal": None, "dietary": None}]


def test_cannot_rsvp_for_guest_on_another_invite(client, admin_headers, household, events):
    other = client.post(
        "/api/admin/households",
        headers=admin_headers,
        json={"name": "The Hsu Family", "guests": [{"full_name": "Wei Hsu"}]},
    ).json()
    res = client.put(
        f"/api/invites/{household['invite_code']}/rsvp",
        json={
            "responses": [
                {
                    "guest_id": other["guests"][0]["id"],
                    "event_id": events[0]["id"],
                    "attending": False,
                }
            ]
        },
    )
    assert res.status_code == 422


def test_cannot_rsvp_for_event_not_invited_to(client, admin_headers, events):
    korea_only = client.post(
        "/api/admin/households",
        headers=admin_headers,
        json={"name": "Seoul Friends", "guests": [{"full_name": "A"}], "event_slugs": ["korea"]},
    ).json()
    assert [e["slug"] for e in korea_only["events"]] == ["korea"]
    res = client.put(
        f"/api/invites/{korea_only['invite_code']}/rsvp",
        json={
            "responses": [
                {
                    "guest_id": korea_only["guests"][0]["id"],
                    "event_id": events[1]["id"],
                    "attending": True,
                }
            ]
        },
    )
    assert res.status_code == 422

import pytest

from tests.conftest import make_household


def rsvp(client, code, *responses, note=None):
    """Answer by typed code (the token path is covered in test_invite_token.py)."""
    body = {"code": code, "responses": responses, "note": note}
    return client.put("/api/invites/rsvp", json=body)


def yes(event, party_size, meals, zodiacs=None, dietary=None):
    return {
        "event_id": event["id"],
        "attending": True,
        "party_size": party_size,
        "meals": meals,
        "zodiacs": zodiacs or {},
        "dietary": dietary,
    }


def no(event):
    return {"event_id": event["id"], "attending": False}


def declined(event):
    return {
        "event_id": event["id"],
        "attending": False,
        "party_size": 0,
        "meals": {},
        "zodiacs": {},
        "dietary": None,
    }


def test_lookup_is_case_and_dash_insensitive(client, household, events):
    code = household["invite_code"]
    messy = f" {code[:3].lower()}-{code[3:].lower()} "
    res = client.post("/api/invites/lookup", json={"code": messy})
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Kim Family"
    assert (body["contact_first_name"], body["contact_last_name"]) == ("Minji", "Kim")
    assert body["max_guests"] == 3
    assert body["primary_event_id"] == events[0]["id"]
    assert [e["slug"] for e in body["events"]] == ["korea", "taiwan"]  # sorted by date
    assert body["events"][0]["gift_zodiacs"] == ["rooster", "rat"]
    # Guests never see admin fields (or the token: they already have it).
    assert not {"invite_code", "invite_token", "invite_url"} & body.keys()
    assert "capacity" not in body["events"][0]


def test_unknown_code_returns_404(client):
    res = client.post("/api/invites/lookup", json={"code": "ZZZZZZ"})
    assert res.status_code == 404


def test_rsvp_per_event(client, household, events):
    korea, taiwan = events
    res = rsvp(
        client,
        household["invite_code"],
        yes(korea, 3, {"beef": 1, "fish": 1, "kids": 1}, {"rat": 1}, "no shellfish"),
        no(taiwan),
        note="Can't wait!",
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["rsvps"] == [
        {
            "event_id": korea["id"],
            "attending": True,
            "party_size": 3,
            "meals": {"beef": 1, "fish": 1, "kids": 1},
            "zodiacs": {"rat": 1},
            "dietary": "no shellfish",
        },
        declined(taiwan),
    ]
    assert body["note"] == "Can't wait!"
    assert body["responded_at"] is not None


def test_resubmit_updates_and_declining_clears_counts(client, household, events):
    code, korea = household["invite_code"], events[0]
    rsvp(client, code, yes(korea, 2, {"fish": 2}, {"rooster": 1}))
    res = rsvp(client, code, {**yes(korea, 2, {"fish": 2}, {"rooster": 1}), "attending": False})
    assert res.json()["rsvps"] == [declined(korea)]


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param({"party_size": 4, "meals": {"fish": 4}}, id="over-max-guests"),
        pytest.param({"party_size": 0, "meals": {}}, id="zero-people-attending"),
        pytest.param({"party_size": 2, "meals": {"fish": 1}}, id="meals-dont-add-up"),
        pytest.param(
            {"party_size": 2, "meals": {"fish": 2}, "zodiacs": {"dragon": 1}},
            id="zodiac-not-asked-at-korea",
        ),
        pytest.param(
            {"party_size": 2, "meals": {"fish": 2}, "zodiacs": {"rat": 3}},
            id="more-zodiac-than-people",
        ),
    ],
)
def test_invalid_answers_rejected(client, household, events, answer):
    body = {"event_id": events[0]["id"], "attending": True, **answer}
    assert rsvp(client, household["invite_code"], body).status_code == 422


def test_cannot_rsvp_for_event_not_invited_to(client, admin_headers, events):
    korea_only = make_household(client, admin_headers, name="Seoul Friends")
    assert [e["slug"] for e in korea_only["events"]] == ["korea"]
    res = rsvp(client, korea_only["invite_code"], yes(events[1], 1, {"fish": 1}))
    assert res.status_code == 422

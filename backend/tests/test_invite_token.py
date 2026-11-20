from tests.conftest import make_household


def lookup(client, **cred):
    return client.post("/api/invites/lookup", json=cred)


def test_household_gets_long_token_and_link(household):
    token = household["invite_token"]
    assert len(token) >= 22
    assert token != household["invite_code"]
    assert household["invite_url"] == f"http://localhost:3000/invite/{token}"


def test_tokens_are_unique(client, admin_headers, events):
    tokens = {make_household(client, admin_headers, name=f"H{i}")["invite_token"] for i in range(5)}
    assert len(tokens) == 5


def test_lookup_by_token_or_code_finds_same_household(client, household):
    by_token = lookup(client, token=household["invite_token"])
    by_code = lookup(client, code=household["invite_code"])
    assert by_token.status_code == by_code.status_code == 200
    assert by_token.json() == by_code.json()


def test_unknown_token_returns_404(client, household):
    assert lookup(client, token="x" * 22).status_code == 404


def test_token_is_case_sensitive(client, household):
    token = household["invite_token"]
    flipped = token.swapcase()
    if flipped != token:
        assert lookup(client, token=flipped).status_code == 404


def test_must_send_exactly_one_of_token_or_code(client, household):
    assert lookup(client).status_code == 422
    both = lookup(client, token=household["invite_token"], code=household["invite_code"])
    assert both.status_code == 422


def test_rsvp_by_token(client, household, events):
    answer = {"event_id": events[0]["id"], "attending": True, "party_size": 1, "meals": {"fish": 1}}
    res = client.put(
        "/api/invites/rsvp", json={"token": household["invite_token"], "responses": [answer]}
    )
    assert res.status_code == 200, res.text
    assert res.json()["rsvps"][0]["party_size"] == 1


def test_rotate_token_kills_old_link_keeps_code(client, admin_headers, household):
    old = household["invite_token"]
    res = client.post(
        f"/api/admin/households/{household['id']}/rotate-token", headers=admin_headers
    )
    assert res.status_code == 200
    new = res.json()
    assert new["invite_token"] != old
    assert new["invite_url"].endswith(new["invite_token"])
    assert new["invite_code"] == household["invite_code"]

    assert lookup(client, token=old).status_code == 404
    assert lookup(client, token=new["invite_token"]).status_code == 200
    assert lookup(client, code=household["invite_code"]).status_code == 200


def test_rotate_token_requires_admin(client, household):
    res = client.post(f"/api/admin/households/{household['id']}/rotate-token")
    assert res.status_code == 401

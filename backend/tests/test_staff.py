import pytest

from app.models.user import MAX_FAILED_LOGINS
from tests.conftest import make_household

PIN = "482913"


def create_helper(client, admin_headers, username="wei", name="Uncle Wei", pin=PIN):
    res = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"name": name, "username": username, "pin": pin},
    )
    assert res.status_code == 201, res.text
    return res.json()


def staff_login(client, username="wei", pin=PIN):
    return client.post("/api/staff/login", json={"username": username, "pin": pin})


@pytest.fixture
def helper(client, admin_headers):
    return create_helper(client, admin_headers)


@pytest.fixture
def helper_headers(client, helper):
    res = staff_login(client)
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def url(household, event, what):
    return f"/api/staff/households/{household['id']}/{what}/{event['id']}"


# ---------- Accounts & login ----------


def test_helper_account_is_a_manager(helper):
    assert helper["role"] == "manager"
    assert helper["active"] is True
    assert helper["locked"] is False
    assert "pin_hash" not in helper


def test_login_and_me(client, helper_headers):
    me = client.get("/api/staff/me", headers=helper_headers).json()
    assert me == {"role": "manager", "name": "Uncle Wei"}


def test_username_is_case_insensitive(client, helper):
    assert staff_login(client, username=" WEI ").status_code == 200


def test_wrong_pin_or_unknown_user(client, helper):
    assert staff_login(client, pin="000000").status_code == 401
    assert staff_login(client, username="nobody").status_code == 401


@pytest.mark.parametrize("pin", ["12345", "123456789", "12345a"])
def test_pin_must_be_6_to_8_digits(client, admin_headers, pin):
    res = client.post(
        "/api/admin/users", headers=admin_headers, json={"name": "X", "username": "x", "pin": pin}
    )
    assert res.status_code == 422


def test_duplicate_username_conflicts(client, admin_headers, helper):
    res = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"name": "Other", "username": "Wei", "pin": PIN},
    )
    assert res.status_code == 409


def test_locks_after_too_many_wrong_pins_and_new_pin_unlocks(client, admin_headers, helper):
    for _ in range(MAX_FAILED_LOGINS):
        assert staff_login(client, pin="000000").status_code == 401
    assert staff_login(client).status_code == 403  # even the right PIN
    users = client.get("/api/admin/users", headers=admin_headers).json()
    assert users[0]["locked"] is True

    res = client.patch(
        f"/api/admin/users/{helper['id']}", headers=admin_headers, json={"pin": "11112222"}
    )
    assert res.json()["locked"] is False
    assert staff_login(client, pin="11112222").status_code == 200


def test_right_pin_resets_failed_count(client, helper):
    for _ in range(MAX_FAILED_LOGINS - 1):
        staff_login(client, pin="000000")
    assert staff_login(client).status_code == 200
    for _ in range(MAX_FAILED_LOGINS - 1):
        staff_login(client, pin="000000")
    assert staff_login(client).status_code == 200  # not locked: count started over


def test_disabling_helper_signs_them_out(client, admin_headers, helper, helper_headers):
    client.patch(f"/api/admin/users/{helper['id']}", headers=admin_headers, json={"active": False})
    assert client.get("/api/staff/me", headers=helper_headers).status_code == 401
    assert staff_login(client).status_code == 401


def test_helpers_cannot_use_admin_api(client, helper_headers):
    assert client.get("/api/admin/households", headers=helper_headers).status_code == 403
    assert client.get("/api/admin/users", headers=helper_headers).status_code == 403


def test_staff_api_needs_login(client, household):
    assert (
        client.post("/api/staff/scan", json={"token": household["invite_token"]}).status_code == 401
    )
    assert client.get("/api/staff/households", params={"q": "kim"}).status_code == 401


def test_admin_can_use_staff_api(client, admin_headers, household):
    res = client.post(
        "/api/staff/scan", headers=admin_headers, json={"token": household["invite_token"]}
    )
    assert res.status_code == 200


# ---------- Finding a household ----------


def test_scan_qr(client, helper_headers, household):
    res = client.post(
        "/api/staff/scan", headers=helper_headers, json={"token": household["invite_token"]}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == household["id"]
    assert body["name"] == "Kim Family"
    assert body["check_ins"] == [] and body["gifts"] == []
    assert "invite_token" not in body  # helpers don't need the secret


def test_scan_unknown_qr(client, helper_headers, household):
    res = client.post("/api/staff/scan", headers=helper_headers, json={"token": "x" * 22})
    assert res.status_code == 404


def test_search_by_household_or_contact_name(client, admin_headers, helper_headers, household):
    make_household(client, admin_headers, name="Hsu Family", contact_first_name="Dingnan")

    def names(q):
        res = client.get("/api/staff/households", headers=helper_headers, params={"q": q})
        return [h["name"] for h in res.json()]

    assert names("kim") == ["Kim Family"]
    assert names("minji") == ["Kim Family"]  # contact first name
    assert names("family") == ["Hsu Family", "Kim Family"]
    assert names("hsu dingnan") == ["Hsu Family"]  # every word must match
    assert names("nobody") == []


# ---------- Check-in ----------


def test_check_in_records_who_and_can_be_updated(client, helper_headers, household, events):
    korea = events[0]
    res = client.put(
        url(household, korea, "check-ins"), headers=helper_headers, json={"arrived": 2}
    )
    assert res.status_code == 200, res.text
    [c] = res.json()["check_ins"]
    assert (c["event_id"], c["arrived"], c["checked_in_by_name"]) == (korea["id"], 2, "Uncle Wei")

    # Scanning again updates the same record instead of adding another.
    res = client.put(
        url(household, korea, "check-ins"), headers=helper_headers, json={"arrived": 3}
    )
    assert [c["arrived"] for c in res.json()["check_ins"]] == [3]


def test_undo_check_in(client, helper_headers, household, events):
    client.put(url(household, events[0], "check-ins"), headers=helper_headers, json={"arrived": 1})
    res = client.delete(url(household, events[0], "check-ins"), headers=helper_headers)
    assert res.json()["check_ins"] == []


def test_cannot_check_in_to_event_not_invited(client, admin_headers, helper_headers, events):
    korea_only = make_household(client, admin_headers, name="Seoul Friends")
    res = client.put(
        url(korea_only, events[1], "check-ins"), headers=helper_headers, json={"arrived": 1}
    )
    assert res.status_code == 422


def test_arrived_must_be_at_least_one(client, helper_headers, household, events):
    res = client.put(
        url(household, events[0], "check-ins"), headers=helper_headers, json={"arrived": 0}
    )
    assert res.status_code == 422


def test_admin_password_check_in_has_no_name(client, admin_headers, household, events):
    res = client.put(
        url(household, events[0], "check-ins"), headers=admin_headers, json={"arrived": 1}
    )
    assert res.json()["check_ins"][0]["checked_in_by_name"] is None


# ---------- Gifts ----------


def test_record_gift(client, helper_headers, household, events):
    korea = events[0]
    body = {"amount": 100000, "zodiac_gifts": {"rat": 1, "rooster": 0}, "note": "2 envelopes"}
    res = client.put(url(household, korea, "gifts"), headers=helper_headers, json=body)
    assert res.status_code == 200, res.text
    [g] = res.json()["gifts"]
    assert g["amount"] == 100000
    assert g["zodiac_gifts"] == {"rat": 1}  # zero counts dropped
    assert g["note"] == "2 envelopes"
    assert g["recorded_by_name"] == "Uncle Wei"

    res = client.put(url(household, korea, "gifts"), headers=helper_headers, json={"amount": 50000})
    assert [(g["amount"], g["zodiac_gifts"]) for g in res.json()["gifts"]] == [(50000, {})]


def test_gift_zodiac_must_be_events_animal(client, helper_headers, household, events):
    body = {"amount": 0, "zodiac_gifts": {"dragon": 1}}  # dragon is Taiwan's, not Korea's
    res = client.put(url(household, events[0], "gifts"), headers=helper_headers, json=body)
    assert res.status_code == 422


def test_clear_gift(client, helper_headers, household, events):
    client.put(url(household, events[0], "gifts"), headers=helper_headers, json={"amount": 1})
    res = client.delete(url(household, events[0], "gifts"), headers=helper_headers)
    assert res.json()["gifts"] == []


def test_gifts_never_reach_guests(client, helper_headers, household, events):
    client.put(url(household, events[0], "gifts"), headers=helper_headers, json={"amount": 1})
    body = client.post("/api/invites/lookup", json={"token": household["invite_token"]}).json()
    assert not {"gifts", "check_ins"} & body.keys()


# ---------- Max people ----------


def test_helper_can_change_max_guests(client, helper_headers, household):
    res = client.put(
        f"/api/staff/households/{household['id']}/max-guests",
        headers=helper_headers,
        json={"max_guests": 5},
    )
    assert res.status_code == 200
    assert res.json()["max_guests"] == 5


def test_helper_max_guests_respects_capacity(
    client, admin_headers, helper_headers, household, events
):
    client.patch(
        f"/api/admin/events/{events[0]['id']}", headers=admin_headers, json={"capacity": 4}
    )
    res = client.put(
        f"/api/staff/households/{household['id']}/max-guests",
        headers=helper_headers,
        json={"max_guests": 5},
    )
    assert res.status_code == 409


# ---------- Admin totals ----------


def test_summary_and_export_include_wedding_day(
    client, admin_headers, helper_headers, household, events
):
    korea = events[0]
    client.put(url(household, korea, "check-ins"), headers=helper_headers, json={"arrived": 3})
    client.put(
        url(household, korea, "gifts"),
        headers=helper_headers,
        json={"amount": 100000, "zodiac_gifts": {"rat": 1}},
    )
    s = client.get("/api/admin/summary", headers=admin_headers).json()["events"][0]
    assert s["households_checked_in"] == 1
    assert s["people_arrived"] == 3
    assert s["gift_total"] == 100000
    assert s["zodiac_gifts_given"] == {"rat": 1}

    lines = client.get("/api/admin/export.csv", headers=admin_headers).text.splitlines()
    header = lines[0].split(",")
    korea_row = dict(zip(header, lines[1].split(","), strict=True))
    assert korea_row["arrived"] == "3"
    assert korea_row["gift_amount"] == "100000"
    assert korea_row["zodiac_gift_rat"] == "1"


def test_deleting_helper_keeps_their_records(
    client, admin_headers, helper, helper_headers, household, events
):
    client.put(url(household, events[0], "check-ins"), headers=helper_headers, json={"arrived": 1})
    assert (
        client.delete(f"/api/admin/users/{helper['id']}", headers=admin_headers).status_code == 204
    )
    res = client.get(f"/api/staff/households/{household['id']}", headers=admin_headers).json()
    assert res["check_ins"][0]["arrived"] == 1
    assert res["check_ins"][0]["checked_in_by_name"] is None

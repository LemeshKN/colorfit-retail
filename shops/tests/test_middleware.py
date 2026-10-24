import uuid

import pytest

pytestmark = pytest.mark.django_db


def test_cookie_is_set_with_right_flags(client):
    response = client.get("/")
    morsel = response.cookies["cf_device"]
    uuid.UUID(morsel.value)  # raises if not a UUID
    assert morsel["httponly"] is True
    assert morsel["samesite"] == "Lax"
    assert int(morsel["max-age"]) == 60 * 60 * 24 * 365


def test_existing_valid_cookie_is_kept(client):
    existing = str(uuid.uuid4())
    client.cookies["cf_device"] = existing
    response = client.get("/")
    assert "cf_device" not in response.cookies


def test_invalid_cookie_is_replaced(client):
    client.cookies["cf_device"] = "not-a-uuid"
    response = client.get("/")
    uuid.UUID(response.cookies["cf_device"].value)
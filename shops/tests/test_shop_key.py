import pytest
from django.core.cache import cache

from shops.models import Shop
from shops.services import (
    KeyLockedError,
    check_shop_key,
    set_shop_key,
    shop_needs_key,
)

DEVICE = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def shop(db):
    return Shop.objects.create(
        name="Test Shop", code="T-1", slug="t-1", city="Test City"
    )


def test_shop_without_key_lets_everyone_in(shop):
    assert shop_needs_key(shop) is False
    assert check_shop_key(shop, "anything", DEVICE) is True


def test_key_is_stored_as_hash_not_text(shop):
    set_shop_key(shop, "secret-1")
    shop.refresh_from_db()
    assert shop_needs_key(shop) is True
    assert "secret-1" not in shop.access_key_hash


def test_short_key_is_rejected(shop):
    with pytest.raises(ValueError):
        set_shop_key(shop, "abc")


def test_empty_key_removes_the_key(shop):
    set_shop_key(shop, "secret-1")
    set_shop_key(shop, "")
    assert shop_needs_key(shop) is False


def test_right_key_passes_and_wrong_key_fails(shop):
    set_shop_key(shop, "secret-1")
    assert check_shop_key(shop, " secret-1 ", DEVICE) is True
    assert check_shop_key(shop, "wrong-key", DEVICE) is False


def test_five_wrong_tries_lock_the_device(shop):
    set_shop_key(shop, "secret-1")
    for _ in range(5):
        assert check_shop_key(shop, "wrong-key", DEVICE) is False
    with pytest.raises(KeyLockedError):
        check_shop_key(shop, "secret-1", DEVICE)


def test_lock_is_per_device(shop):
    set_shop_key(shop, "secret-1")
    for _ in range(5):
        check_shop_key(shop, "wrong-key", DEVICE)
    other = "22222222-2222-2222-2222-222222222222"
    assert check_shop_key(shop, "secret-1", other) is True


def test_right_key_clears_the_wrong_count(shop):
    set_shop_key(shop, "secret-1")
    for _ in range(4):
        check_shop_key(shop, "wrong-key", DEVICE)
    assert check_shop_key(shop, "secret-1", DEVICE) is True
    for _ in range(4):
        assert check_shop_key(shop, "wrong-key", DEVICE) is False
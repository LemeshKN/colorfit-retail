import pytest
from django.core.cache import cache
from django.urls import reverse

from shops.models import Shop
from shops.services import check_shop_key, set_shop_key, shop_needs_key

DEVICE = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def shop(db):
    return Shop.objects.create(
        name="Test Shop", code="T-1", slug="t-1", city="Test City"
    )


def post_change(admin_client, shop, **extra):
    data = {
        "name": shop.name,
        "code": shop.code,
        "slug": shop.slug,
        "city": shop.city,
        "is_active": "on",
    }
    data.update(extra)
    return admin_client.post(reverse("admin:shops_shop_change", args=[shop.pk]), data)


def test_admin_can_set_a_key(admin_client, shop):
    response = post_change(admin_client, shop, new_pass_key="secret-1")
    assert response.status_code == 302
    shop.refresh_from_db()
    assert shop_needs_key(shop) is True
    assert check_shop_key(shop, "secret-1", DEVICE) is True


def test_short_key_is_rejected(admin_client, shop):
    response = post_change(admin_client, shop, new_pass_key="abc")
    assert response.status_code == 200
    shop.refresh_from_db()
    assert shop_needs_key(shop) is False


def test_blank_field_keeps_the_current_key(admin_client, shop):
    set_shop_key(shop, "secret-1")
    response = post_change(admin_client, shop, new_pass_key="")
    assert response.status_code == 302
    shop.refresh_from_db()
    assert check_shop_key(shop, "secret-1", DEVICE) is True


def test_remove_box_removes_the_key(admin_client, shop):
    set_shop_key(shop, "secret-1")
    post_change(admin_client, shop, remove_pass_key="on")
    shop.refresh_from_db()
    assert shop_needs_key(shop) is False


def test_hash_is_never_shown_on_the_page(admin_client, shop):
    set_shop_key(shop, "secret-1")
    page = admin_client.get(reverse("admin:shops_shop_change", args=[shop.pk]))
    assert "pbkdf2" not in page.content.decode()
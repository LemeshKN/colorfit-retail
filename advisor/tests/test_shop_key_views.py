import pytest
from django.core.cache import cache
from django.urls import reverse

from catalog.models import CardCode, SkinTone
from shops.models import AdviceSession, Shop
from shops.services import set_shop_key


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def card(db):
    tone = SkinTone.objects.create(label="Tone 1")
    return CardCode.objects.create(code="ST-07", skin_tone=tone, is_active=True)


@pytest.fixture
def keyed_shop(db):
    shop = Shop.objects.create(name="Keyed", code="K-1", slug="k-1", city="Test City")
    set_shop_key(shop, "secret-1")
    return shop


@pytest.fixture
def open_shop(db):
    return Shop.objects.create(name="Open", code="O-1", slug="o-1", city="Test City")


def test_menu_page_opens_and_shows_privacy_line(client, open_shop):
    response = client.get(reverse("advisor:shop_menu", args=[open_shop.slug]))
    assert response.status_code == 200
    assert "does not store your name or photo" in response.content.decode()


def test_card_page_asks_for_key_when_shop_has_one(client, keyed_shop):
    response = client.get(reverse("advisor:card_entry", args=[keyed_shop.slug]))
    assert 'name="shop_key"' in response.content.decode()


def test_card_page_has_no_key_field_without_a_key(client, open_shop):
    response = client.get(reverse("advisor:card_entry", args=[open_shop.slug]))
    assert 'name="shop_key"' not in response.content.decode()


def test_wrong_key_saves_no_session(client, keyed_shop, card):
    response = client.post(
        reverse("advisor:card_entry", args=[keyed_shop.slug]),
        {"card_id": "ST-07", "shop_key": "wrong-key"},
    )
    assert response.status_code == 200
    assert AdviceSession.objects.count() == 0


def test_right_key_and_card_save_one_session(client, keyed_shop, card):
    response = client.post(
        reverse("advisor:card_entry", args=[keyed_shop.slug]),
        {"card_id": "ST-07", "shop_key": "secret-1"},
    )
    assert response.status_code == 302
    assert AdviceSession.objects.count() == 1


def test_shop_without_key_works_without_a_key(client, open_shop, card):
    response = client.post(
        reverse("advisor:card_entry", args=[open_shop.slug]),
        {"card_id": "ST-07"},
    )
    assert response.status_code == 302
    assert AdviceSession.objects.count() == 1
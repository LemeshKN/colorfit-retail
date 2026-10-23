import pytest

from advisor.services import get_remembered_card, remember_card
from catalog.tests.factories import CardCodeFactory
from shops.tests.factories import ShopFactory

pytestmark = pytest.mark.django_db


def test_remembered_card_is_returned_for_same_shop():
    shop, card = ShopFactory(), CardCodeFactory(code="ST-07")
    session = {}
    remember_card(session, shop, card)
    assert get_remembered_card(session, shop) == card


def test_empty_session_returns_none():
    assert get_remembered_card({}, ShopFactory()) is None


def test_card_is_not_valid_for_another_shop():
    shop, other = ShopFactory(), ShopFactory()
    session = {}
    remember_card(session, shop, CardCodeFactory())
    assert get_remembered_card(session, other) is None


def test_deactivated_card_is_dropped():
    shop, card = ShopFactory(), CardCodeFactory()
    session = {}
    remember_card(session, shop, card)
    card.is_active = False
    card.save()
    assert get_remembered_card(session, shop) is None
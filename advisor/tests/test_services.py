import pytest

from advisor.services import (
    ADVICE_SESSION_KEY,
    attach_garment,
    get_remembered_card,
    remember_card,
    start_visit,
)
from catalog.tests.factories import CardCodeFactory, GarmentTypeFactory
from shops.models import AdviceSession
from shops.tests.factories import ShopFactory

pytestmark = pytest.mark.django_db

DEVICE = "11111111-1111-4111-8111-111111111111"


# Tests from Level 3: remembering the card


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


# Tests from Level 4: saving the visit and the garment


def test_start_visit_saves_row_and_remembers_id():
    shop, card, store = ShopFactory(), CardCodeFactory(), {}
    row = start_visit(store, shop, card, DEVICE)
    assert AdviceSession.objects.count() == 1
    assert store[ADVICE_SESSION_KEY] == row.pk


def test_attach_garment_fills_garment():
    shop, card, garment, store = (
        ShopFactory(),
        CardCodeFactory(),
        GarmentTypeFactory(),
        {},
    )
    row = start_visit(store, shop, card, DEVICE)
    attach_garment(store, shop, garment)
    row.refresh_from_db()
    assert row.garment == garment


def test_attach_garment_handles_missing_id():
    assert attach_garment({}, ShopFactory(), GarmentTypeFactory()) is None


def test_attach_garment_ignores_row_from_other_shop():
    shop, other, card = ShopFactory(), ShopFactory(), CardCodeFactory()
    store = {}
    start_visit(store, shop, card, DEVICE)
    assert attach_garment(store, other, GarmentTypeFactory()) is None
    assert ADVICE_SESSION_KEY not in store
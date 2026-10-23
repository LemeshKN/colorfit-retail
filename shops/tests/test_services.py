import datetime
import uuid

import pytest

from catalog.services import InvalidCardError, resolve_card
from catalog.tests.factories import CardCodeFactory, GarmentTypeFactory
from shops.models import AdviceSession
from shops.services import record_session, set_session_garment, unique_visits_report, get_active_shop, list_active_shops

from .factories import AdviceSessionFactory, ShopFactory

pytestmark = pytest.mark.django_db

DAY = datetime.date(2026, 10, 20)


def test_invalid_card_saves_no_session():
    ShopFactory()
    with pytest.raises(InvalidCardError):
        resolve_card("ST-99")
    assert AdviceSession.objects.count() == 0


def test_inactive_card_saves_no_session():
    shop = ShopFactory()
    card = CardCodeFactory(is_active=False)
    with pytest.raises(InvalidCardError):
        record_session(shop, card, str(uuid.uuid4()))
    assert AdviceSession.objects.count() == 0


def test_valid_card_saves_one_session():
    shop = ShopFactory()
    card = CardCodeFactory(code="ST-07")
    device = str(uuid.uuid4())

    session = record_session(shop, resolve_card("st7"), device)

    assert AdviceSession.objects.count() == 1
    assert session.shop == shop
    assert session.card_code == card
    assert session.garment is None
    assert str(session.device_id) == device


def test_every_valid_entry_is_saved():
    shop, card = ShopFactory(), CardCodeFactory()
    device = str(uuid.uuid4())
    record_session(shop, card, device)
    record_session(shop, card, device)
    assert AdviceSession.objects.count() == 2


def test_set_session_garment_fills_garment():
    session = AdviceSessionFactory()
    garment = GarmentTypeFactory()
    set_session_garment(session, garment)
    session.refresh_from_db()
    assert session.garment == garment
    assert AdviceSession.objects.count() == 1


def test_report_counts_40_total_and_31_unique():
    shop = ShopFactory()
    devices = [str(uuid.uuid4()) for _ in range(31)]
    for device in devices + devices[:9]:  # 31 + 9 repeats = 40 entries
        AdviceSessionFactory(shop=shop, device_id=device, local_date=DAY)

    report = unique_visits_report(shop, (DAY, DAY))

    assert report["total_entries"] == 40
    assert report["unique_devices"] == 31
    assert report["counted_visits"] == 31
    assert report["days"] == [
        {"date": DAY, "entries": 40, "unique_devices": 31, "repeats": 9}
    ]


def test_same_device_on_two_days_counts_two_visits():
    shop, device = ShopFactory(), str(uuid.uuid4())
    day2 = DAY + datetime.timedelta(days=1)
    AdviceSessionFactory(shop=shop, device_id=device, local_date=DAY)
    AdviceSessionFactory(shop=shop, device_id=device, local_date=DAY)
    AdviceSessionFactory(shop=shop, device_id=device, local_date=day2)

    report = unique_visits_report(shop, (DAY, day2))

    assert report["total_entries"] == 3
    assert report["unique_devices"] == 1
    assert report["counted_visits"] == 2
    assert [d["repeats"] for d in report["days"]] == [1, 0]


def test_report_ignores_other_shops_and_dates_outside_range():
    shop, other_shop = ShopFactory(), ShopFactory()
    AdviceSessionFactory(shop=shop, local_date=DAY)
    AdviceSessionFactory(shop=other_shop, local_date=DAY)
    AdviceSessionFactory(shop=shop, local_date=DAY - datetime.timedelta(days=5))

    report = unique_visits_report(shop, (DAY, DAY))
    assert report["total_entries"] == 1


def test_report_for_empty_range_is_zero():
    report = unique_visits_report(ShopFactory(), (DAY, DAY))
    assert report["total_entries"] == 0
    assert report["unique_devices"] == 0
    assert report["days"] == []

def test_get_active_shop_ignores_case_and_inactive_shops():
    shop = ShopFactory(slug="sh-014")
    ShopFactory(slug="sh-015", is_active=False)
    assert get_active_shop("SH-014") == shop
    assert get_active_shop("sh-015") is None
    assert get_active_shop("nope") is None


def test_list_active_shops_hides_inactive_shops():
    live = ShopFactory()
    ShopFactory(is_active=False)
    assert list(list_active_shops()) == [live]
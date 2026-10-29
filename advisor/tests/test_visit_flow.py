import pytest

from catalog.tests.factories import CardCodeFactory, GarmentTypeFactory
from shops.models import AdviceSession
from shops.tests.factories import ShopFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def shop():
    return ShopFactory(slug="sh-014", code="SH-014", is_active=True)


def test_valid_card_saves_one_session(client, shop):
    CardCodeFactory(code="ST-07", is_active=True)
    client.post("/s/sh-014/tone/", {"card_id": "st-7"})
    assert AdviceSession.objects.count() == 1
    row = AdviceSession.objects.get()
    assert row.garment is None
    assert str(row.device_id) == client.cookies["cf_device"].value
    assert client.session["advice_session_id"] == row.pk


def test_invalid_card_saves_no_session(client, shop):
    response = client.post("/s/sh-014/tone/", {"card_id": "ZZ-99"})
    assert response.status_code == 200  # form shown again with an error
    assert AdviceSession.objects.count() == 0


def test_inactive_card_saves_no_session(client, shop):
    CardCodeFactory(code="ST-08", is_active=False)
    response = client.post("/s/sh-014/tone/", {"card_id": "ST-08"})
    assert response.status_code == 200
    assert AdviceSession.objects.count() == 0


def test_colors_page_sets_garment(client, shop):
    CardCodeFactory(code="ST-07", is_active=True)
    shirt = GarmentTypeFactory(slug="shirt")
    client.post("/s/sh-014/tone/", {"card_id": "ST-07"})
    response = client.get("/s/sh-014/colors/shirt/")
    assert response.status_code == 200
    assert AdviceSession.objects.get().garment == shirt


def test_colors_page_works_when_saved_id_is_missing(client, shop):
    CardCodeFactory(code="ST-07", is_active=True)
    GarmentTypeFactory(slug="shirt")
    client.post("/s/sh-014/tone/", {"card_id": "ST-07"})
    AdviceSession.objects.all().delete()
    response = client.get("/s/sh-014/colors/shirt/")
    assert response.status_code == 200
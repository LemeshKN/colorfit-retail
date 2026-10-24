import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.tests.factories import CardCodeFactory
from shops.services import record_session
from shops.tests.factories import ShopFactory

pytestmark = pytest.mark.django_db
URL = "/admin/shops/advicesession/report/"


def test_report_needs_staff_login(client):
    response = client.get(URL)
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


def test_non_staff_user_is_blocked(client):
    user = get_user_model().objects.create_user("cust", password="pw12345!", is_staff=False)
    client.force_login(user)
    response = client.get(URL)
    assert response.status_code == 302


def test_report_shows_40_total_and_31_unique(admin_client):
    shop, card = ShopFactory(), CardCodeFactory()
    devices = [str(uuid.uuid4()) for _ in range(31)]
    for device in devices:
        record_session(shop, card, device)
    for device in devices[:9]:  # 9 repeats, so 40 entries in total
        record_session(shop, card, device)

    today = timezone.localdate().isoformat()
    response = admin_client.get(URL, {"shop": shop.pk, "start": today, "end": today})

    assert response.status_code == 200
    assert response.context["report"]["total_entries"] == 40
    assert response.context["report"]["unique_devices"] == 31
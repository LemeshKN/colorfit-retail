import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from api.views import CardResolveThrottle
from catalog.tests.factories import (
    BottomColorFactory,
    BottomTypeFactory,
    CardCodeFactory,
    ColorFamilyFactory,
    GarmentTypeFactory,
    OutfitPairingFactory,
    ShadeFactory,
    ShadeRecommendationFactory,
    SkinToneFactory,
)
from shops.models import AdviceSession
from shops.tests.factories import ShopFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


# Garments and families


def test_garment_with_pairing_lists_its_bottom_types(api):
    jeans = BottomTypeFactory(name="Jeans", slug="jeans")
    shirt = GarmentTypeFactory(name="Shirt", slug="shirt", has_pairing=True)
    shirt.bottom_types.add(jeans)
    data = api.get("/api/v1/garments/").json()
    row = next(g for g in data if g["slug"] == "shirt")
    assert row["has_pairing"] is True
    assert [b["slug"] for b in row["bottom_types"]] == ["jeans"]


def test_womens_kurta_has_no_pairing(api):
    GarmentTypeFactory(name="Women's Kurta", slug="womens-kurta", has_pairing=False)
    data = api.get("/api/v1/garments/").json()
    row = next(g for g in data if g["slug"] == "womens-kurta")
    assert row["has_pairing"] is False
    assert row["bottom_types"] == []


def test_families_come_in_sort_order(api):
    ColorFamilyFactory(name="Second", slug="second", sort_order=2)
    ColorFamilyFactory(name="First", slug="first", sort_order=1)
    data = api.get("/api/v1/families/").json()
    assert [f["slug"] for f in data] == ["first", "second"]


# Card resolve


def test_resolve_valid_card_cleans_input(api):
    CardCodeFactory(code="ST-07", skin_tone=SkinToneFactory(label="Tone 4"))
    response = api.post("/api/v1/cards/resolve/", {"card": " st-7 "}, format="json")
    assert response.status_code == 200
    assert response.json() == {"card": "ST-07", "tone": "Tone 4"}


def test_resolve_unknown_card_is_404(api):
    response = api.post("/api/v1/cards/resolve/", {"card": "ZZ-99"}, format="json")
    assert response.status_code == 404


def test_resolve_inactive_card_is_404(api):
    CardCodeFactory(code="ST-08", is_active=False)
    response = api.post("/api/v1/cards/resolve/", {"card": "ST-08"}, format="json")
    assert response.status_code == 404


def test_resolve_without_card_field_is_400(api):
    response = api.post("/api/v1/cards/resolve/", {}, format="json")
    assert response.status_code == 400


def test_resolve_saves_no_session(api):
    CardCodeFactory(code="ST-07")
    ShopFactory()
    api.post("/api/v1/cards/resolve/", {"card": "ST-07"}, format="json")
    assert AdviceSession.objects.count() == 0


def test_resolve_is_rate_limited(api, monkeypatch):
    monkeypatch.setitem(CardResolveThrottle.THROTTLE_RATES, "card_resolve", "3/min")
    CardCodeFactory(code="ST-07")
    codes = [
        api.post("/api/v1/cards/resolve/", {"card": "ST-07"}, format="json").status_code
        for _ in range(4)
    ]
    assert codes == [200, 200, 200, 429]


# Shades


def test_shades_hide_hidden_statuses_and_put_best_first(api):
    tone = SkinToneFactory()
    family = ColorFamilyFactory(slug="maroon")
    CardCodeFactory(code="ST-07", skin_tone=tone)
    for name, status in [
        ("A", "usually_avoid"),
        ("B", "good"),
        ("C", "try_carefully"),
        ("D", "best"),
    ]:
        shade = ShadeFactory(family=family, name=name)
        ShadeRecommendationFactory(skin_tone=tone, shade=shade, status=status)

    data = api.get("/api/v1/shades/", {"card": "ST-07", "family": "maroon"}).json()

    assert [s["name"] for s in data] == ["D", "B"]
    assert [s["label"] for s in data] == ["Best for you", "Good option"]
    assert "status" not in data[0]


def test_shades_unknown_family_is_404(api):
    CardCodeFactory(code="ST-07")
    response = api.get("/api/v1/shades/", {"card": "ST-07", "family": "nope"})
    assert response.status_code == 404


def test_shades_unknown_card_is_404(api):
    ColorFamilyFactory(slug="maroon")
    response = api.get("/api/v1/shades/", {"card": "ZZ-99", "family": "maroon"})
    assert response.status_code == 404


def test_shades_missing_params_is_400(api):
    assert api.get("/api/v1/shades/", {"card": "ST-07"}).status_code == 400
    assert api.get("/api/v1/shades/", {"family": "maroon"}).status_code == 400


# Pairings


def test_pairing_shade_override_comes_first(api):
    family = ColorFamilyFactory()
    shade = ShadeFactory(family=family)
    jeans = BottomTypeFactory(slug="jeans")
    grey = BottomColorFactory(name="Grey")
    navy = BottomColorFactory(name="Navy")
    OutfitPairingFactory(
        top_family=family, top_shade=None, bottom_type=jeans, bottom_color=grey, rank=1
    )
    OutfitPairingFactory(
        top_family=family, top_shade=shade, bottom_type=jeans, bottom_color=navy, rank=1
    )

    data = api.get("/api/v1/pairings/", {"shade": shade.pk, "bottom_type": "jeans"}).json()

    assert data[0]["name"] == "Navy"


def test_pairings_bad_shade_is_400(api):
    BottomTypeFactory(slug="jeans")
    response = api.get("/api/v1/pairings/", {"shade": "abc", "bottom_type": "jeans"})
    assert response.status_code == 400


def test_pairings_unknown_shade_is_404(api):
    BottomTypeFactory(slug="jeans")
    response = api.get("/api/v1/pairings/", {"shade": 999999, "bottom_type": "jeans"})
    assert response.status_code == 404


# API matches the pages


def test_api_shades_match_shades_page(client, api):
    ShopFactory(slug="sh-014", code="SH-014", is_active=True)
    tone = SkinToneFactory()
    family = ColorFamilyFactory(slug="maroon")
    CardCodeFactory(code="ST-07", skin_tone=tone, is_active=True)
    GarmentTypeFactory(slug="shirt")
    for status in ["good", "best", "good", "usually_avoid"]:
        shade = ShadeFactory(family=family)
        ShadeRecommendationFactory(skin_tone=tone, shade=shade, status=status)

    client.post("/s/sh-014/tone/", {"card_id": "ST-07"})
    page = client.get("/s/sh-014/shades/shirt/maroon/")
    page_ids = [r.shade_id for r in page.context["recommendations"]]
    api_ids = [
        s["id"]
        for s in api.get("/api/v1/shades/", {"card": "ST-07", "family": "maroon"}).json()
    ]

    assert page_ids == api_ids
    assert len(api_ids) == 3


def test_api_pairings_match_pairing_page(client, api):
    ShopFactory(slug="sh-014", code="SH-014", is_active=True)
    family = ColorFamilyFactory()
    shade = ShadeFactory(family=family)
    jeans = BottomTypeFactory(slug="jeans")
    shirt = GarmentTypeFactory(slug="shirt", has_pairing=True)
    shirt.bottom_types.add(jeans)
    CardCodeFactory(code="ST-07", is_active=True)
    for rank in (2, 1, 3):
        OutfitPairingFactory(
            top_family=family,
            top_shade=None,
            bottom_type=jeans,
            bottom_color=BottomColorFactory(),
            rank=rank,
        )

    client.post("/s/sh-014/tone/", {"card_id": "ST-07"})
    page = client.get(f"/s/sh-014/pairing/shirt/{shade.pk}/jeans/")
    page_ids = [p.bottom_color_id for p in page.context["pairings"]]
    api_ids = [
        p["bottom_color_id"]
        for p in api.get("/api/v1/pairings/", {"shade": shade.pk, "bottom_type": "jeans"}).json()
    ]

    assert page_ids == api_ids
    assert len(api_ids) == 3
import pytest
from django.core.management import call_command

from catalog.services import (
    InvalidCardError,
    check_catalog_health,
    get_bottom_previews,
    get_bottom_type,
    get_bottom_types,
    get_family,
    get_garment,
    get_pairings,
    get_shade,
    get_visible_shades,
    list_families,
    list_garments,
    normalize_card_code,
    resolve_card,
)

from .factories import (
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

pytestmark = pytest.mark.django_db


# normalize_card_code

@pytest.mark.parametrize(
    "raw", ["st-7", "ST07", " ST-07 ", "St 7", "ST-07", "st - 7", "ST-007"]
)
def test_normalize_card_code(raw):
    assert normalize_card_code(raw) == "ST-07"


def test_normalize_handles_empty_and_none():
    assert normalize_card_code("") == ""
    assert normalize_card_code(None) == ""


# resolve_card

def test_resolve_card_accepts_messy_input():
    card = CardCodeFactory(code="ST-07")
    assert resolve_card(" st7 ") == card


def test_inactive_card_is_rejected():
    CardCodeFactory(code="ST-07", is_active=False)
    with pytest.raises(InvalidCardError):
        resolve_card("ST-07")


def test_unknown_card_is_rejected():
    with pytest.raises(InvalidCardError):
        resolve_card("ST-99")


# get_visible_shades

def _recommend(tone, family, status):
    return ShadeRecommendationFactory(
        skin_tone=tone, shade=ShadeFactory(family=family), status=status
    )


def test_hidden_statuses_are_never_shown():
    tone, family = SkinToneFactory(), ColorFamilyFactory()
    _recommend(tone, family, "best")
    _recommend(tone, family, "good")
    _recommend(tone, family, "try_carefully")
    _recommend(tone, family, "usually_avoid")

    statuses = {r.status for r in get_visible_shades(tone, family)}
    assert statuses == {"best", "good"}


def test_best_comes_before_good():
    tone, family = SkinToneFactory(), ColorFamilyFactory()
    _recommend(tone, family, "good")
    _recommend(tone, family, "best")
    _recommend(tone, family, "good")
    _recommend(tone, family, "best")

    statuses = [r.status for r in get_visible_shades(tone, family)]
    assert statuses == ["best", "best", "good", "good"]


def test_visible_shades_only_for_that_tone_and_family():
    tone, other_tone = SkinToneFactory(), SkinToneFactory()
    family, other_family = ColorFamilyFactory(), ColorFamilyFactory()
    mine = _recommend(tone, family, "best")
    _recommend(other_tone, family, "best")
    _recommend(tone, other_family, "best")

    assert list(get_visible_shades(tone, family)) == [mine]


# get_bottom_types

def test_womens_kurta_has_no_pairing():
    jeans = BottomTypeFactory()
    womens_kurta = GarmentTypeFactory(name="Women's Kurta", has_pairing=False)
    womens_kurta.bottom_types.add(jeans)  # even if linked by mistake
    assert list(get_bottom_types(womens_kurta)) == []


def test_pairing_garment_returns_its_bottom_types():
    jeans, chinos = BottomTypeFactory(), BottomTypeFactory()
    shirt = GarmentTypeFactory(name="Shirt", has_pairing=True)
    shirt.bottom_types.add(jeans, chinos)
    assert set(get_bottom_types(shirt)) == {jeans, chinos}


# get_pairings

def test_family_rule_is_used_when_no_override():
    family, bottom = ColorFamilyFactory(), BottomTypeFactory()
    shade = ShadeFactory(family=family)
    rule = OutfitPairingFactory(top_family=family, bottom_type=bottom)
    assert list(get_pairings(shade, bottom)) == [rule]


def test_shade_override_beats_family_rule():
    family, bottom = ColorFamilyFactory(), BottomTypeFactory()
    shade = ShadeFactory(family=family)
    OutfitPairingFactory(top_family=family, bottom_type=bottom)
    override = OutfitPairingFactory(
        top_family=family, top_shade=shade, bottom_type=bottom
    )
    assert list(get_pairings(shade, bottom)) == [override]


def test_override_for_another_shade_does_not_change_this_shade():
    family, bottom = ColorFamilyFactory(), BottomTypeFactory()
    shade, other = ShadeFactory(family=family), ShadeFactory(family=family)
    rule = OutfitPairingFactory(top_family=family, bottom_type=bottom)
    OutfitPairingFactory(top_family=family, top_shade=other, bottom_type=bottom)
    assert list(get_pairings(shade, bottom)) == [rule]


def test_pairings_are_ordered_by_rank():
    family, bottom = ColorFamilyFactory(), BottomTypeFactory()
    shade = ShadeFactory(family=family)
    third = OutfitPairingFactory(top_family=family, bottom_type=bottom, rank=3)
    first = OutfitPairingFactory(top_family=family, bottom_type=bottom, rank=1)
    second = OutfitPairingFactory(top_family=family, bottom_type=bottom, rank=2)
    assert list(get_pairings(shade, bottom)) == [first, second, third]


# check_catalog_health

def test_health_fails_below_three_visible_shades():
    tone, family = SkinToneFactory(), ColorFamilyFactory()
    _recommend(tone, family, "best")
    _recommend(tone, family, "good")
    _recommend(tone, family, "try_carefully")  # hidden, does not count

    report = check_catalog_health()
    assert not report.is_ok
    assert report.short_shades == [{"tone": tone, "family": family, "visible": 2}]


def test_health_passes_with_three_visible_shades():
    tone, family = SkinToneFactory(), ColorFamilyFactory()
    for status in ("best", "good", "good"):
        _recommend(tone, family, status)

    report = check_catalog_health()
    assert report.short_shades == []
    assert report.is_ok


def test_health_reports_missing_pairing_rule():
    family, jeans = ColorFamilyFactory(), BottomTypeFactory()
    shirt = GarmentTypeFactory(name="Shirt", has_pairing=True)
    shirt.bottom_types.add(jeans)

    report = check_catalog_health()
    assert report.missing_pairings == [{"family": family, "bottom_type": jeans}]

    OutfitPairingFactory(top_family=family, bottom_type=jeans)
    assert check_catalog_health().missing_pairings == []


def test_health_ignores_bottom_types_of_garments_without_pairing():
    ColorFamilyFactory()
    womens_kurta = GarmentTypeFactory(has_pairing=False)
    womens_kurta.bottom_types.add(BottomTypeFactory())
    assert check_catalog_health().missing_pairings == []


def test_seeded_catalog_has_enough_visible_shades():
    call_command("seed_catalog")
    call_command("load_recommendations")
    report = check_catalog_health()
    assert report.short_shades == []
    # Pairing rows are entered by hand in admin, so they are not checked here.

def test_admin_action_reports_short_shades(admin_client):
    tone, family = SkinToneFactory(), ColorFamilyFactory()
    _recommend(tone, family, "best")

    response = admin_client.post(
        "/admin/catalog/colorfamily/",
        {
            "action": "run_catalog_health_check",
            "_selected_action": [family.pk],
        },
        follow=True,
    )

    assert response.status_code == 200
    assert "It needs at least 3" in response.content.decode()


# lookups used by the pages

def test_list_garments_returns_all():
    a, b = GarmentTypeFactory(), GarmentTypeFactory()
    assert set(list_garments()) == {a, b}


def test_get_garment_by_slug():
    garment = GarmentTypeFactory(slug="shirt")
    assert get_garment("shirt") == garment
    assert get_garment("nope") is None


def test_list_families_in_sort_order_with_sample_hex():
    second = ColorFamilyFactory(sort_order=2)
    first = ColorFamilyFactory(sort_order=1)
    ShadeFactory(family=first, hex="#112233")

    families = list(list_families())

    assert families == [first, second]
    assert families[0].sample_hex == "#112233"
    assert families[1].sample_hex is None


def test_get_family_shade_and_bottom_type():
    family = ColorFamilyFactory(slug="maroon")
    shade = ShadeFactory(family=family)
    bottom = BottomTypeFactory(slug="jeans")

    assert get_family("maroon") == family
    assert get_family("nope") is None
    assert get_shade(shade.pk) == shade
    assert get_shade(999999) is None
    assert get_bottom_type("jeans") == bottom
    assert get_bottom_type("nope") is None


@pytest.mark.django_db
def test_bottom_previews_give_colors_in_rank_order_per_type():
    shade = ShadeFactory()
    jeans, chinos = BottomTypeFactory(), BottomTypeFactory()
    c1, c2, c3 = (BottomColorFactory() for _ in range(3))
    OutfitPairingFactory(top_family=shade.family, bottom_type=jeans, bottom_color=c2, rank=2)
    OutfitPairingFactory(top_family=shade.family, bottom_type=jeans, bottom_color=c1, rank=1)
    OutfitPairingFactory(top_family=shade.family, bottom_type=chinos, bottom_color=c3, rank=1)

    previews = get_bottom_previews(shade, [jeans, chinos])

    assert [p["bottom"] for p in previews] == [jeans, chinos]
    assert previews[0]["colors"] == [c1, c2]
    assert previews[1]["colors"] == [c3]


@pytest.mark.django_db
def test_bottom_previews_empty_when_no_rule():
    shade = ShadeFactory()
    previews = get_bottom_previews(shade, [BottomTypeFactory()])
    assert previews[0]["colors"] == []
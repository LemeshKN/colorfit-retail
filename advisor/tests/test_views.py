from types import SimpleNamespace

import pytest
from django.urls import reverse

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
from shops.tests.factories import ShopFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def world():
    shop = ShopFactory(name="Raipur Cloth House", slug="sh-014", code="SH-014")
    tone = SkinToneFactory()
    CardCodeFactory(code="ST-07", skin_tone=tone)

    family = ColorFamilyFactory(slug="maroon", name="Maroon")
    best = ShadeFactory(family=family, name="Burgundy")
    good = ShadeFactory(family=family, name="Wine")
    hidden = ShadeFactory(family=family, name="Hidden Rust")
    ShadeRecommendationFactory(skin_tone=tone, shade=good, status="good")
    ShadeRecommendationFactory(skin_tone=tone, shade=best, status="best")
    ShadeRecommendationFactory(skin_tone=tone, shade=hidden, status="try_carefully")

    jeans = BottomTypeFactory(name="Jeans", slug="jeans")
    shirt = GarmentTypeFactory(name="Shirt", slug="shirt", has_pairing=True)
    shirt.bottom_types.add(jeans)
    womens = GarmentTypeFactory(
        name="Women's Kurta", slug="womens-kurta", has_pairing=False
    )
    OutfitPairingFactory(
        top_family=family,
        bottom_type=jeans,
        bottom_color=BottomColorFactory(name="Navy Blue"),
    )
    return SimpleNamespace(
        shop=shop, family=family, best=best, shirt=shirt, womens=womens, jeans=jeans
    )


def _enter_card(client, text="st7"):
    url = reverse("advisor:card_entry", kwargs={"shop_slug": "sh-014"})
    return client.post(url, {"card_id": text})

def _shades_url(world, garment):
    return reverse(
        "advisor:shades",
        kwargs={"shop_slug": "sh-014", "garment_slug": garment.slug, "family_slug": "maroon"},
    )


def test_full_flow_for_a_shop(client, world):
    response = _enter_card(client, " st7 ")
    assert response.status_code == 302

    garments = client.get(reverse("advisor:garments", kwargs={"shop_slug": "sh-014"}))
    assert garments.status_code == 200
    assert "Shirt" in garments.content.decode()

    colors = client.get(
        reverse("advisor:colors", kwargs={"shop_slug": "sh-014", "garment_slug": "shirt"})
    )
    assert "Maroon" in colors.content.decode()

    shades = client.get(_shades_url(world, world.shirt))
    assert "Burgundy" in shades.content.decode()

    bottoms = client.get(
        reverse(
            "advisor:pairing_bottoms",
            kwargs={"shop_slug": "sh-014", "garment_slug": "shirt", "shade_id": world.best.pk},
        )
    )
    assert "Jeans" in bottoms.content.decode()

    pairing = client.get(
        reverse(
            "advisor:pairing",
            kwargs={
                "shop_slug": "sh-014",
                "garment_slug": "shirt",
                "shade_id": world.best.pk,
                "bottom_slug": "jeans",
            },
        )
    )
    assert pairing.status_code == 200
    assert "Navy Blue" in pairing.content.decode()


def test_public_visitor_sees_only_the_find_a_shop_page(client, world):
    home = client.get("/")
    assert home.status_code == 200
    assert "Raipur Cloth House" in home.content.decode()

    card_page = reverse("advisor:card_entry", kwargs={"shop_slug": "sh-014"})
    protected = [
        reverse("advisor:garments", kwargs={"shop_slug": "sh-014"}),
        reverse("advisor:colors", kwargs={"shop_slug": "sh-014", "garment_slug": "shirt"}),
        _shades_url(world, world.shirt),
        reverse(
            "advisor:pairing_bottoms",
            kwargs={"shop_slug": "sh-014", "garment_slug": "shirt", "shade_id": world.best.pk},
        ),
    ]
    for url in protected:
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == card_page


def test_invalid_card_shows_error_and_keeps_user_out(client, world):
    response = _enter_card(client, "ST-99")
    assert response.status_code == 200
    assert "could not find this card ID" in response.content.decode()
    garments = client.get(reverse("advisor:garments", kwargs={"shop_slug": "sh-014"}))
    assert garments.status_code == 302


def test_hidden_statuses_are_not_on_the_page(client, world):
    _enter_card(client)
    html = client.get(_shades_url(world, world.shirt)).content.decode()
    assert "Hidden Rust" not in html
    assert "Try carefully" not in html
    assert "Usually avoid" not in html


def test_best_is_listed_before_good_and_labels_are_right(client, world):
    _enter_card(client)
    html = client.get(_shades_url(world, world.shirt)).content.decode()
    assert html.index("Burgundy") < html.index("Wine")
    assert "Best for you" in html
    assert "Good option" in html


def test_womens_kurta_shades_show_no_pairing_link(client, world):
    _enter_card(client)
    html = client.get(_shades_url(world, world.womens)).content.decode()
    assert "Burgundy" in html
    assert "matching bottom-wear" not in html


def test_womens_kurta_pairing_page_is_404(client, world):
    _enter_card(client)
    url = reverse(
        "advisor:pairing_bottoms",
        kwargs={"shop_slug": "sh-014", "garment_slug": "womens-kurta", "shade_id": world.best.pk},
    )
    assert client.get(url).status_code == 404


def test_bottom_type_not_linked_to_garment_is_404(client, world):
    BottomTypeFactory(name="Pyjama", slug="pyjama")
    _enter_card(client)
    url = reverse(
        "advisor:pairing",
        kwargs={
            "shop_slug": "sh-014",
            "garment_slug": "shirt",
            "shade_id": world.best.pk,
            "bottom_slug": "pyjama",
        },
    )
    assert client.get(url).status_code == 404


def test_card_entered_at_one_shop_does_not_open_another_shop(client, world):
    ShopFactory(slug="sh-015", code="SH-015")
    _enter_card(client)
    response = client.get(reverse("advisor:garments", kwargs={"shop_slug": "sh-015"}))
    assert response.status_code == 302


def test_unknown_or_inactive_shop_is_404(client, world):
    ShopFactory(slug="sh-016", is_active=False)
    assert client.get("/s/nope/").status_code == 404
    assert client.get("/s/sh-016/").status_code == 404


def test_card_page_shows_privacy_line(client, world):
    html = client.get("/s/sh-014/").content.decode()
    assert "does not store your name or photo" in html

def _bottoms_url(world):
    return reverse(
        "advisor:pairing_bottoms",
        kwargs={
            "shop_slug": "sh-014",
            "garment_slug": "shirt",
            "shade_id": world.best.pk,
        },
    )


def test_bottom_type_card_shows_its_three_colors_in_rank_order(client, world):
    OutfitPairingFactory(
        top_family=world.family,
        bottom_type=world.jeans,
        bottom_color=BottomColorFactory(name="Charcoal Grey"),
        rank=3,
    )
    OutfitPairingFactory(
        top_family=world.family,
        bottom_type=world.jeans,
        bottom_color=BottomColorFactory(name="Off White Test"),
        rank=2,
    )
    _enter_card(client)
    html = client.get(_bottoms_url(world)).content.decode()

    assert "Navy Blue" in html
    assert "Off White Test" in html
    assert "Charcoal Grey" in html
    assert (
        html.index("Navy Blue")
        < html.index("Off White Test")
        < html.index("Charcoal Grey")
    )


def test_bottom_page_shows_top_shade_hint_and_pairing_link(client, world):
    _enter_card(client)
    html = client.get(_bottoms_url(world)).content.decode()

    assert "Burgundy" in html  # the chosen top shade
    assert "Casual" in html  # hint for Jeans
    pairing_url = reverse(
        "advisor:pairing",
        kwargs={
            "shop_slug": "sh-014",
            "garment_slug": "shirt",
            "shade_id": world.best.pk,
            "bottom_slug": "jeans",
        },
    )
    assert pairing_url in html



def test_shades_page_shows_each_group_heading_once_in_order(client, world):
    _enter_card(client)
    html = client.get(_shades_url(world, world.shirt)).content.decode()

    assert html.count("Best for you") == 1
    assert html.count("Good option") == 1
    assert (
        html.index("Best for you")
        < html.index("Burgundy")
        < html.index("Good option")
        < html.index("Wine")
    )


def test_shades_for_garment_with_pairing_link_to_bottoms(client, world):
    _enter_card(client)
    html = client.get(_shades_url(world, world.shirt)).content.decode()
    link = reverse(
        "advisor:pairing_bottoms",
        kwargs={
            "shop_slug": "sh-014",
            "garment_slug": "shirt",
            "shade_id": world.best.pk,
        },
    )
    assert link in html
    assert "Match bottoms" in html


def test_shades_for_garment_without_pairing_have_no_links(client, world):
    _enter_card(client)
    html = client.get(_shades_url(world, world.womens)).content.decode()
    link = reverse(
        "advisor:pairing_bottoms",
        kwargs={
            "shop_slug": "sh-014",
            "garment_slug": "womens-kurta",
            "shade_id": world.best.pk,
        },
    )
    assert "Burgundy" in html
    assert link not in html
    assert "Match bottoms" not in html

def test_colors_page_lists_every_family(client, world):
    for i in range(9):
        ColorFamilyFactory(name=f"Hue {i}", slug=f"hue-{i}")
    _enter_card(client)
    html = client.get(
        reverse("advisor:colors", kwargs={"shop_slug": "sh-014", "garment_slug": "shirt"})
    ).content.decode()
    assert "Maroon" in html
    for i in range(9):
        assert f"Hue {i}" in html
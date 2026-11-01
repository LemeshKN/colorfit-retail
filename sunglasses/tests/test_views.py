import pytest
from django.urls import reverse

from shops.models import Shop
from sunglasses.models import FaceShapeRule, FrameStyle


@pytest.fixture
def shop(db):
    return Shop.objects.create(
        name="Test Shop", code="T-1", slug="t-1", city="Test City"
    )


@pytest.fixture
def on(settings):
    settings.SUNGLASSES_ENABLED = True


def make_shape(name, order=1, active=True):
    return FaceShapeRule.objects.create(
        name=name,
        slug=name.lower(),
        sort_order=order,
        length_ratio=1.4,
        forehead_ratio=0.85,
        jaw_ratio=0.75,
        is_active=active,
    )


def make_frame(shape, name, rank):
    return FrameStyle.objects.create(
        shape=shape,
        name=name,
        slug=name.lower(),
        image_file=f"img/frames/{name.lower()}.svg",
        note=f"{name} note",
        rank=rank,
    )


def url(name, shop, *args):
    return reverse(f"sunglasses:{name}", args=[shop.slug, *args])


def test_every_page_is_404_when_switch_is_off(client, shop, settings):
    settings.SUNGLASSES_ENABLED = False
    make_shape("Oval")
    assert client.get(url("intro", shop)).status_code == 404
    assert client.get(url("shapes", shop)).status_code == 404
    assert client.get(url("shape_detail", shop, "oval")).status_code == 404
    assert client.get(url("unclear", shop)).status_code == 404


def test_menu_hides_button_when_switch_is_off(client, shop, settings):
    settings.SUNGLASSES_ENABLED = False
    html = client.get(reverse("advisor:shop_menu", args=[shop.slug])).content.decode()
    assert url("intro", shop) not in html


def test_menu_shows_button_when_switch_is_on(client, shop, on):
    html = client.get(reverse("advisor:shop_menu", args=[shop.slug])).content.decode()
    assert url("intro", shop) in html


def test_unknown_shop_is_404(client, db, on):
    response = client.get("/s/nope/sunglasses/")
    assert response.status_code == 404


def test_intro_page_opens(client, shop, on):
    assert client.get(url("intro", shop)).status_code == 200


def test_shapes_page_lists_active_shapes_only(client, shop, on):
    make_shape("Oval", 1)
    make_shape("Square", 2, active=False)
    html = client.get(url("shapes", shop)).content.decode()
    assert "Oval" in html
    assert "Square" not in html


def test_frames_come_first_in_rank_order_then_the_shape(client, shop, on):
    oval = make_shape("Oval")
    make_frame(oval, "Second", 2)
    make_frame(oval, "First", 1)
    html = client.get(url("shape_detail", shop, "oval")).content.decode()
    assert html.index("First</p>") < html.index("Second</p>") < html.index("Face shape:")
    assert "First note" in html
    assert "Try frames on and choose what you like." in html
    assert "often suit this face shape" not in html
    assert "Colors on your screen vary" not in html


def test_photo_note_appears_only_after_a_photo(client, shop, on):
    make_shape("Oval")
    base = url("shape_detail", shop, "oval")
    plain = client.get(base).content.decode()
    assert "Your photo was not saved." not in plain
    after = client.get(base + "?source=photo").content.decode()
    assert "Your photo was not saved." in after

def test_try_again_link_goes_to_the_photo_page(client, shop, on):
    make_shape("Oval")
    html = client.get(url("shape_detail", shop, "oval")).content.decode()
    assert "Not like your face? Try again" in html
    assert url("intro", shop) in html
    assert "Try another photo" not in html


def test_also_possible_link_keeps_the_photo_flag(client, shop, on):
    make_shape("Oval", 1)
    make_shape("Square", 2)
    html = client.get(
        url("shape_detail", shop, "oval") + "?also=square&source=photo"
    ).content.decode()
    assert url("shape_detail", shop, "square") + "?source=photo" in html

def test_inactive_shape_is_404(client, shop, on):
    make_shape("Oval", active=False)
    assert client.get(url("shape_detail", shop, "oval")).status_code == 404


def test_also_possible_link_shows_for_a_valid_shape(client, shop, on):
    make_shape("Oval", 1)
    make_shape("Square", 2)
    html = client.get(url("shape_detail", shop, "oval") + "?also=square").content.decode()
    assert "Also possible:" in html
    assert url("shape_detail", shop, "square") in html


def test_also_possible_is_ignored_for_unknown_or_same_shape(client, shop, on):
    make_shape("Oval", 1)
    for query in ("?also=nope", "?also=oval", "?also="):
        html = client.get(url("shape_detail", shop, "oval") + query).content.decode()
        assert "Also possible:" not in html


def test_unclear_page_shows_the_reason(client, shop, on):
    html = client.get(url("unclear", shop) + "?reason=small").content.decode()
    assert "too small" in html


def test_unclear_page_uses_a_safe_default_for_unknown_reason(client, shop, on):
    html = client.get(url("unclear", shop) + "?reason=<script>").content.decode()
    assert "could not get a clear styling suggestion" in html
    assert "<script>" not in html

def test_intro_has_both_photo_buttons_and_the_privacy_note(client, shop, on):
    html = client.get(url("intro", shop)).content.decode()
    assert 'capture="user"' in html
    assert "Choose a photo" in html
    assert "not uploaded or saved" in html
    assert "/api/v1/sunglasses/classify/" in html


def test_cut_off_reason_has_its_own_message(client, shop, on):
    html = client.get(url("unclear", shop) + "?reason=cut_off").content.decode()
    assert "outside the photo" in html
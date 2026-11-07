import pytest
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.core.management import call_command

from sunglasses.admin import FrameStyleAdmin
from sunglasses.models import FaceShapeRule, FrameStyle
from sunglasses.services import apply_tryon_urls
from sunglasses.validators import validate_cloudinary_url

GOOD = "https://res.cloudinary.com/demo/image/upload/v1/round.png"
OTHER = "https://res.cloudinary.com/demo/image/upload/v1/oval.png"


def make_shape(slug):
    return FaceShapeRule.objects.create(
        name=slug, slug=slug, length_ratio=1.3, forehead_ratio=0.9, jaw_ratio=0.8
    )


def make_frame(shape, slug, rank):
    return FrameStyle.objects.create(
        shape=shape,
        name=slug,
        slug=slug,
        image_file=f"img/frames/{slug}.svg",
        note="note",
        rank=rank,
    )


@pytest.fixture
def frames(db):
    a, b = make_shape("shape-a"), make_shape("shape-b")
    return [
        make_frame(a, "round", 1),
        make_frame(a, "oval", 2),
        make_frame(b, "round", 1),
    ]


def test_validator_accepts_cloudinary_https():
    validate_cloudinary_url(GOOD)


@pytest.mark.parametrize(
    "bad",
    [
        "http://res.cloudinary.com/x.png",
        "https://example.com/x.png",
        "https://res.cloudinary.com.evil.com/x.png",
        "https://res.cloudinary.com@evil.com/x.png",
    ],
)
def test_validator_rejects_other_links(bad):
    with pytest.raises(ValidationError):
        validate_cloudinary_url(bad)


def test_new_frame_has_defaults(frames):
    assert frames[0].tryon_image_url == ""
    assert frames[0].tryon_width_factor == 1.6


@pytest.mark.parametrize("factor", [0.5, 5])
def test_width_factor_out_of_range_fails(frames, factor):
    frames[0].tryon_width_factor = factor
    with pytest.raises(ValidationError):
        frames[0].full_clean()


def test_apply_updates_every_row_with_the_slug(frames):
    counts = apply_tryon_urls({"round": GOOD})
    assert counts == {"round": 2}
    urls = {f.slug: f.tryon_image_url for f in FrameStyle.objects.all()}
    assert urls["round"] == GOOD
    assert urls["oval"] == ""


def test_apply_reports_unknown_slug_as_zero(frames):
    assert apply_tryon_urls({"missing": GOOD}) == {"missing": 0}


def test_apply_with_one_bad_link_changes_nothing(frames):
    with pytest.raises(ValidationError):
        apply_tryon_urls({"round": GOOD, "oval": "https://example.com/x.png"})
    assert FrameStyle.objects.exclude(tryon_image_url="").count() == 0


def test_apply_twice_gives_the_same_result(frames):
    apply_tryon_urls({"round": GOOD})
    assert apply_tryon_urls({"round": GOOD}) == {"round": 2}


def test_command_sets_links(frames, monkeypatch):
    monkeypatch.setattr("sunglasses.management.commands.set_tryon_urls.TRYON_URLS", {"oval": OTHER})
    call_command("set_tryon_urls")
    assert FrameStyle.objects.get(slug="oval").tryon_image_url == OTHER


def test_admin_shows_whether_a_frame_has_tryon(frames):
    model_admin = FrameStyleAdmin(FrameStyle, AdminSite())
    assert model_admin.has_tryon(frames[0]) is False
    apply_tryon_urls({"round": GOOD})
    frames[0].refresh_from_db()
    assert model_admin.has_tryon(frames[0]) is True

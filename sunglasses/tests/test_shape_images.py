import pytest
from django.core.exceptions import ValidationError

from sunglasses.models import FaceShapeRule
from sunglasses.services import apply_shape_image_urls

GOOD = "https://res.cloudinary.com/demo/image/upload/v1/shape-oval.png"


@pytest.fixture
def shape(db):
    return FaceShapeRule.objects.create(
        name="Oval", slug="oval", length_ratio=1.3, forehead_ratio=0.9, jaw_ratio=0.8
    )


def test_new_shape_has_no_picture_link(shape):
    assert shape.image_url == ""


def test_apply_sets_the_link_by_slug(shape):
    assert apply_shape_image_urls({"oval": GOOD}) == {"oval": 1}
    shape.refresh_from_db()
    assert shape.image_url == GOOD


def test_unknown_slug_counts_zero(shape):
    assert apply_shape_image_urls({"missing": GOOD}) == {"missing": 0}


def test_one_bad_link_changes_nothing(shape):
    with pytest.raises(ValidationError):
        apply_shape_image_urls({"oval": GOOD, "round": "https://example.com/x.png"})
    shape.refresh_from_db()
    assert shape.image_url == ""
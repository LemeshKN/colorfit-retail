import pytest
from django.db import IntegrityError, transaction

from sunglasses.models import FaceShapeRule, FrameStyle


def make_shape(name):
    # These numbers are only placeholders for the test.
    return FaceShapeRule.objects.create(
        name=name,
        slug=name.lower(),
        length_ratio=1.5,
        forehead_ratio=0.9,
        jaw_ratio=0.8,
    )


def make_frame(shape, slug, rank):
    return FrameStyle.objects.create(
        shape=shape,
        name=slug.title(),
        slug=slug,
        image_file=f"img/frames/{slug}.svg",
        note="Test note",
        rank=rank,
    )


@pytest.mark.django_db
def test_same_rank_twice_for_one_shape_is_rejected():
    oval = make_shape("Oval")
    make_frame(oval, "aviator", 1)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_frame(oval, "round", 1)


@pytest.mark.django_db
def test_same_rank_for_two_different_shapes_is_fine():
    make_frame(make_shape("Oval"), "aviator", 1)
    make_frame(make_shape("Round"), "aviator", 1)
    assert FrameStyle.objects.count() == 2
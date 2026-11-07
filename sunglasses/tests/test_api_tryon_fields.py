import pytest

from api.serializers import FrameStyleSerializer
from sunglasses.models import FaceShapeRule, FrameStyle

LINK = "https://res.cloudinary.com/demo/image/upload/v1/round.png"


@pytest.fixture
def frame(db):
    shape = FaceShapeRule.objects.create(
        name="Oval", slug="oval", length_ratio=1.3, forehead_ratio=0.9, jaw_ratio=0.8
    )
    return FrameStyle.objects.create(
        shape=shape,
        name="Round",
        slug="round",
        image_file="img/frames/round.svg",
        note="Circular lenses",
        rank=1,
        tryon_image_url=LINK,
        tryon_width_factor=1.7,
    )


def test_frame_serializer_has_the_try_on_fields(frame):
    data = FrameStyleSerializer(frame).data
    assert data["tryon_image_url"] == LINK
    assert data["tryon_width_factor"] == 1.7


def test_frame_serializer_gives_a_picture_link_for_the_card(frame):
    data = FrameStyleSerializer(frame).data
    assert "round" in data["image_url"]
    assert data["image_url"].endswith(".svg")


def test_frame_without_a_link_has_an_empty_try_on_url(frame):
    frame.tryon_image_url = ""
    frame.save()
    assert FrameStyleSerializer(frame).data["tryon_image_url"] == ""
import pytest
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.management.base import CommandError

from sunglasses.models import FrameStyle
from sunglasses.services import check_sunglasses_health


@pytest.fixture
def shapes(db):
    call_command("seed_face_shapes")


def test_seed_creates_18_frame_styles(shapes):
    call_command("seed_frame_styles")
    assert FrameStyle.objects.count() == 18


def test_seed_twice_creates_no_duplicates(shapes):
    call_command("seed_frame_styles")
    call_command("seed_frame_styles")
    assert FrameStyle.objects.count() == 18


def test_seed_does_not_overwrite_an_edited_note(shapes):
    call_command("seed_frame_styles")
    FrameStyle.objects.filter(shape__slug="oval", rank=1).update(note="My own note")
    call_command("seed_frame_styles")
    assert FrameStyle.objects.get(shape__slug="oval", rank=1).note == "My own note"


def test_seed_stops_when_shapes_are_missing(db):
    with pytest.raises(CommandError):
        call_command("seed_frame_styles")


def test_health_check_passes_after_both_seeds(shapes):
    call_command("seed_frame_styles")
    assert check_sunglasses_health().is_ok is True


def test_every_frame_picture_file_exists(shapes):
    call_command("seed_frame_styles")
    for frame in FrameStyle.objects.all():
        assert finders.find(frame.image_file), f"missing: {frame.image_file}"

def test_frame_lines_are_short(shapes):
    call_command("seed_frame_styles")
    assert all(0 < len(frame.note) <= 60 for frame in FrameStyle.objects.all())
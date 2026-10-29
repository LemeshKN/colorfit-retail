import pytest

from sunglasses.models import FaceShapeRule, FrameStyle
from sunglasses.services import (
    InvalidMeasurementError,
    NoShapeRulesError,
    check_sunglasses_health,
    classify_face_shape,
    compute_ratios,
    get_frame_styles,
)


def make_shape(name, length, forehead, jaw, order=1, active=True):
    return FaceShapeRule.objects.create(
        name=name,
        slug=name.lower(),
        sort_order=order,
        length_ratio=length,
        forehead_ratio=forehead,
        jaw_ratio=jaw,
        is_active=active,
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


def test_ratios_are_divided_by_cheekbone_width():
    ratios = compute_ratios(145, 85, 100, 75)
    assert ratios.length == pytest.approx(1.45)
    assert ratios.forehead == pytest.approx(0.85)
    assert ratios.jaw == pytest.approx(0.75)


def test_unit_does_not_matter():
    small = compute_ratios(145, 85, 100, 75)
    large = compute_ratios(1450, 850, 1000, 750)
    assert small == pytest.approx(large)


@pytest.mark.parametrize(
    "numbers",
    [
        (0, 85, 100, 75),
        (-5, 85, 100, 75),
        (float("nan"), 85, 100, 75),
        (float("inf"), 85, 100, 75),
        ("145", 85, 100, 75),
        (True, 85, 100, 75),
        (500, 85, 100, 75),  # length ratio 5.0 is too long
        (145, 5, 100, 75),  # forehead ratio 0.05 is too narrow
    ],
)
def test_bad_numbers_are_rejected(numbers):
    with pytest.raises(InvalidMeasurementError):
        compute_ratios(*numbers)


@pytest.mark.django_db
def test_closest_shape_wins():
    oval = make_shape("Oval", 1.45, 0.85, 0.75, order=1)
    make_shape("Square", 1.20, 0.90, 0.90, order=2)
    result = classify_face_shape(145, 85, 100, 75)
    assert result.primary == oval


@pytest.mark.django_db
def test_close_second_shape_is_offered_as_alternative():
    oval = make_shape("Oval", 1.40, 0.85, 0.75, order=1)
    square = make_shape("Square", 1.40, 0.90, 0.75, order=2)  # 0.05 away
    result = classify_face_shape(140, 85, 100, 75)
    assert result.primary == oval
    assert result.alternative == square


@pytest.mark.django_db
def test_far_second_shape_is_not_offered():
    make_shape("Oval", 1.45, 0.85, 0.75, order=1)
    make_shape("Square", 1.20, 0.90, 0.90, order=2)
    result = classify_face_shape(145, 85, 100, 75)
    assert result.alternative is None


@pytest.mark.django_db
def test_inactive_shape_is_ignored():
    make_shape("Oval", 1.45, 0.85, 0.75, order=1, active=False)
    square = make_shape("Square", 1.20, 0.90, 0.90, order=2)
    result = classify_face_shape(145, 85, 100, 75)
    assert result.primary == square


@pytest.mark.django_db
def test_no_rules_raises():
    with pytest.raises(NoShapeRulesError):
        classify_face_shape(145, 85, 100, 75)


@pytest.mark.django_db
def test_frame_styles_come_in_rank_order():
    oval = make_shape("Oval", 1.45, 0.85, 0.75)
    make_frame(oval, "third", 3)
    make_frame(oval, "first", 1)
    make_frame(oval, "second", 2)
    names = [frame.slug for frame in get_frame_styles(oval)]
    assert names == ["first", "second", "third"]


@pytest.mark.django_db
def test_health_fails_when_shape_count_is_wrong():
    make_shape("Oval", 1.45, 0.85, 0.75)
    report = check_sunglasses_health()
    assert report.is_ok is False
    assert report.shape_count == 1


@pytest.mark.django_db
def test_health_fails_when_a_shape_has_too_few_frames():
    shapes = [
        make_shape(name, 1.4, 0.85, 0.75, order=i)
        for i, name in enumerate(["A", "B", "C", "D", "E", "F"], start=1)
    ]
    for shape in shapes:
        for rank in (1, 2, 3):
            make_frame(shape, f"{shape.slug}{rank}", rank)
    assert check_sunglasses_health().is_ok is True

    FrameStyle.objects.filter(shape=shapes[0], rank=3).delete()
    report = check_sunglasses_health()
    assert report.is_ok is False
    assert report.short_shapes[0]["frames"] == 2
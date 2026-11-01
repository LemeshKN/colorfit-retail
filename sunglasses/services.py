import math
from dataclasses import dataclass, field

from django.db.models import Count

from .models import FaceShapeRule, FrameStyle

EXPECTED_SHAPES = 6
FRAMES_PER_SHAPE = 3

# Starting guesses. Tune these on real photos, with people who agree to it.
ALTERNATIVE_MARGIN = 0.03
LENGTH_RANGE = (0.8, 2.5)
WIDTH_RANGE = (0.3, 1.5)


class InvalidMeasurementError(Exception):
    """The four numbers cannot describe a real face."""


class NoShapeRulesError(Exception):
    """No active face shape rules exist."""


@dataclass(frozen=True)
class Ratios:
    length: float
    forehead: float
    jaw: float


@dataclass(frozen=True)
class ShapeResult:
    primary: FaceShapeRule
    alternative: FaceShapeRule | None


def _positive_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidMeasurementError("Not a number.")
    if not math.isfinite(value) or value <= 0:
        raise InvalidMeasurementError("Not a positive number.")
    return float(value)


def _in_range(value, limits):
    return limits[0] <= value <= limits[1]


def compute_ratios(face_length, forehead_width, cheekbone_width, jaw_width):
    """Divide three widths by the cheekbone width. Reject odd faces."""
    length = _positive_number(face_length)
    forehead = _positive_number(forehead_width)
    cheek = _positive_number(cheekbone_width)
    jaw = _positive_number(jaw_width)
    ratios = Ratios(length / cheek, forehead / cheek, jaw / cheek)
    if not (
        _in_range(ratios.length, LENGTH_RANGE)
        and _in_range(ratios.forehead, WIDTH_RANGE)
        and _in_range(ratios.jaw, WIDTH_RANGE)
    ):
        raise InvalidMeasurementError("The measurements look wrong for a face.")
    return ratios


def _distance(ratios, rule):
    return math.sqrt(
        (ratios.length - rule.length_ratio) ** 2
        + (ratios.forehead - rule.forehead_ratio) ** 2
        + (ratios.jaw - rule.jaw_ratio) ** 2
    )


def classify_face_shape(face_length, forehead_width, cheekbone_width, jaw_width):
    """Return the closest shape, and a second one only if it is nearly as close."""
    ratios = compute_ratios(face_length, forehead_width, cheekbone_width, jaw_width)
    rules = list(FaceShapeRule.objects.filter(is_active=True))
    if not rules:
        raise NoShapeRulesError
    scored = sorted(
        ((_distance(ratios, rule), rule) for rule in rules),
        key=lambda pair: (pair[0], pair[1].sort_order, pair[1].pk),
    )
    alternative = None
    if len(scored) > 1 and scored[1][0] - scored[0][0] <= ALTERNATIVE_MARGIN:
        alternative = scored[1][1]
    return ShapeResult(primary=scored[0][1], alternative=alternative)


def list_active_shapes():
    return FaceShapeRule.objects.filter(is_active=True)


def get_shape(slug):
    return FaceShapeRule.objects.filter(slug=slug, is_active=True).first()


def get_frame_styles(shape):
    """Frame styles for one shape, rank 1 first."""
    return FrameStyle.objects.filter(shape=shape).order_by("rank")


@dataclass
class SunglassesHealthReport:
    shape_count: int | None = None  # set only when the count is not 6
    short_shapes: list = field(default_factory=list)

    @property
    def is_ok(self):
        return self.shape_count is None and not self.short_shapes


def check_sunglasses_health():
    """Six active shapes, three frame styles each."""
    report = SunglassesHealthReport()
    shapes = list(
        FaceShapeRule.objects.filter(is_active=True).annotate(
            n_frames=Count("frame_styles")
        )
    )
    if len(shapes) != EXPECTED_SHAPES:
        report.shape_count = len(shapes)
    for shape in shapes:
        if shape.n_frames < FRAMES_PER_SHAPE:
            report.short_shapes.append({"shape": shape, "frames": shape.n_frames})
    return report
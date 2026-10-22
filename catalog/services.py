import re
from dataclasses import dataclass, field

from django.db.models import Case, Count, IntegerField, Value, When

from .models import (
    BottomType,
    CardCode,
    GarmentType,
    ColorFamily,
    OutfitPairing,
    ShadeRecommendation,
    SkinTone,
)

BEST = "best"
GOOD = "good"
VISIBLE_STATUSES = (BEST, GOOD)
MIN_VISIBLE_SHADES = 3


class InvalidCardError(Exception):
    """The card ID does not exist or is not active."""


_CARD_PATTERN = re.compile(r"^([A-Z]+)[\s-]*(\d+)$")


def normalize_card_code(text):
    """'st-7', 'ST07' and ' ST-07 ' all become 'ST-07'."""
    cleaned = (text or "").strip().upper()
    match = _CARD_PATTERN.match(cleaned)
    if not match:
        return cleaned
    prefix, number = match.groups()
    return f"{prefix}-{int(number):02d}"


def resolve_card(text):
    """Return the active CardCode, or raise InvalidCardError."""
    code = normalize_card_code(text)
    try:
        return CardCode.objects.select_related("skin_tone").get(
            code=code, is_active=True
        )
    except CardCode.DoesNotExist:
        raise InvalidCardError(code) from None


def get_visible_shades(tone, family):
    """Best and good only. Best comes first."""
    return (
        ShadeRecommendation.objects.filter(
            skin_tone=tone,
            shade__family=family,
            status__in=VISIBLE_STATUSES,
        )
        .select_related("shade")
        .annotate(
            status_order=Case(
                When(status=BEST, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("status_order", "shade__id")
    )


def get_bottom_types(garment):
    """Garments without pairing return no bottom types."""
    if not garment.has_pairing:
        return BottomType.objects.none()
    return garment.bottom_types.all()


def get_pairings(shade, bottom_type):
    """Shade override rows first. If none exist, use the family rule."""
    overrides = OutfitPairing.objects.filter(
        top_shade=shade, bottom_type=bottom_type
    )
    if overrides.exists():
        rows = overrides
    else:
        rows = OutfitPairing.objects.filter(
            top_family=shade.family,
            top_shade__isnull=True,
            bottom_type=bottom_type,
        )
    return rows.select_related("bottom_color").order_by("rank", "id")


@dataclass
class HealthReport:
    short_shades: list = field(default_factory=list)
    missing_pairings: list = field(default_factory=list)

    @property
    def is_ok(self):
        return not self.short_shades and not self.missing_pairings


def check_catalog_health():
    report = HealthReport()

    counts = {
        (row["skin_tone"], row["shade__family"]): row["n"]
        for row in ShadeRecommendation.objects.filter(
            status__in=VISIBLE_STATUSES
        )
        .values("skin_tone", "shade__family")
        .annotate(n=Count("id"))
    }
    families = list(ColorFamily.objects.all())
    for tone in SkinTone.objects.all():
        for family in families:
            visible = counts.get((tone.pk, family.pk), 0)
            if visible < MIN_VISIBLE_SHADES:
                report.short_shades.append(
                    {"tone": tone, "family": family, "visible": visible}
                )

    bottom_types = {}
    for garment in GarmentType.objects.filter(has_pairing=True).prefetch_related(
        "bottom_types"
    ):
        for bottom in garment.bottom_types.all():
            bottom_types[bottom.pk] = bottom
    covered = set(
        OutfitPairing.objects.filter(top_shade__isnull=True).values_list(
            "top_family_id", "bottom_type_id"
        )
    )
    for family in families:
        for bottom in bottom_types.values():
            if (family.pk, bottom.pk) not in covered:
                report.missing_pairings.append(
                    {"family": family, "bottom_type": bottom}
                )

    return report
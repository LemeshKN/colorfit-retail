import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from catalog.management.commands.seed_pairings import RULES
from catalog.models import BottomColor, OutfitPairing
from catalog.services import check_catalog_health

# Guess: change this import if your factories file is somewhere else.
from catalog.tests.factories import (
    BottomColorFactory,
    BottomTypeFactory,
    ColorFamilyFactory,
    GarmentTypeFactory,
    OutfitPairingFactory,
    ShadeFactory,
)

EXPECTED_ROWS = 120  # 10 families x 4 bottom types x 3 colors


@pytest.fixture
def catalog_data(db):
    families = {}
    bottom_types = {}
    color_names = set()
    for bottom_slug, by_family in RULES.items():
        bottom_types[bottom_slug] = BottomTypeFactory(
            slug=bottom_slug, name=bottom_slug.title()
        )
        for family_slug, names in by_family.items():
            if family_slug not in families:
                families[family_slug] = ColorFamilyFactory(
                    slug=family_slug, name=family_slug.title()
                )
            color_names.update(names)
    for name in sorted(color_names):
        BottomColorFactory(name=name)

    garment = GarmentTypeFactory(has_pairing=True)
    garment.bottom_types.set(bottom_types.values())
    return {"families": families, "bottom_types": bottom_types}


def test_seed_creates_120_rows(catalog_data):
    call_command("seed_pairings")
    assert OutfitPairing.objects.count() == EXPECTED_ROWS


def test_seed_twice_creates_no_duplicates(catalog_data):
    call_command("seed_pairings")
    call_command("seed_pairings")
    assert OutfitPairing.objects.count() == EXPECTED_ROWS


def test_ranks_are_1_to_3_for_every_rule(catalog_data):
    call_command("seed_pairings")
    for family in catalog_data["families"].values():
        for bottom in catalog_data["bottom_types"].values():
            ranks = list(
                OutfitPairing.objects.filter(
                    top_family=family, bottom_type=bottom, top_shade__isnull=True
                ).values_list("rank", flat=True)
            )
            assert sorted(ranks) == [1, 2, 3]


def test_no_family_and_bottom_type_has_zero_rows(catalog_data):
    call_command("seed_pairings")
    for family in catalog_data["families"].values():
        for bottom in catalog_data["bottom_types"].values():
            assert OutfitPairing.objects.filter(
                top_family=family, bottom_type=bottom, top_shade__isnull=True
            ).exists()


def test_health_check_reports_40_missing_before_and_none_after(catalog_data):
    assert len(check_catalog_health().missing_pairings) == 40
    call_command("seed_pairings")
    assert check_catalog_health().missing_pairings == []


def test_shade_override_rows_are_not_touched(catalog_data):
    family = catalog_data["families"]["red"]
    bottom = catalog_data["bottom_types"]["jeans"]
    shade = ShadeFactory(family=family)
    color = BottomColor.objects.get(name="Khaki")
    override = OutfitPairingFactory(
        top_family=family,
        top_shade=shade,
        bottom_type=bottom,
        bottom_color=color,
        rank=1,
    )
    call_command("seed_pairings")
    override.refresh_from_db()
    assert override.rank == 1
    assert OutfitPairing.objects.filter(top_shade__isnull=False).count() == 1


def test_missing_bottom_color_stops_the_command(catalog_data):
    BottomColor.objects.get(name="Olive").delete()
    with pytest.raises(CommandError, match="Olive"):
        call_command("seed_pairings")
    assert OutfitPairing.objects.count() == 0

def test_table_has_three_different_colors_per_rule():
    for by_family in RULES.values():
        assert len(by_family) == 10
        for names in by_family.values():
            assert len(names) == 3
            assert len(set(names)) == 3


def test_old_family_rules_are_removed_but_overrides_stay(catalog_data):
    family = catalog_data["families"]["red"]
    bottom = catalog_data["bottom_types"]["jeans"]
    # Brown is not in the red jeans rule, so it counts as an old rule.
    old_color = BottomColor.objects.get(name="Brown")
    OutfitPairingFactory(
        top_family=family, bottom_type=bottom, bottom_color=old_color, rank=1
    )
    override = OutfitPairingFactory(
        top_family=family,
        top_shade=ShadeFactory(family=family),
        bottom_type=bottom,
        bottom_color=old_color,
        rank=1,
    )

    call_command("seed_pairings")

    assert not OutfitPairing.objects.filter(
        top_family=family,
        bottom_type=bottom,
        top_shade__isnull=True,
        bottom_color=old_color,
    ).exists()
    assert OutfitPairing.objects.filter(pk=override.pk).exists()
    assert OutfitPairing.objects.filter(top_shade__isnull=True).count() == 120

def test_grey_and_tan_are_created_when_missing(catalog_data):
    BottomColor.objects.filter(name__in=["Grey", "Tan"]).delete()
    call_command("seed_pairings")
    assert BottomColor.objects.filter(name__in=["Grey", "Tan"]).count() == 2
    assert OutfitPairing.objects.count() == EXPECTED_ROWS
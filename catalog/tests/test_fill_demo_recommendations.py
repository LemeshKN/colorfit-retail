import csv

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from catalog.models import ShadeRecommendation
from catalog.services import check_catalog_health, get_visible_shades
from catalog.tests.factories import ColorFamilyFactory, ShadeFactory, SkinToneFactory

VISIBLE = {"best", "good"}
HIDDEN = {"try_carefully", "usually_avoid"}


def make_rows(tones=10, families=10, shades=8):
    return [
        {
            "tone": f"Tone {t}",
            "family": f"Family {f}",
            "shade": f"Shade {f}-{s}",
            "status": "",
        }
        for t in range(1, tones + 1)
        for f in range(1, families + 1)
        for s in range(1, shades + 1)
    ]


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["tone", "family", "shade", "status"])
        writer.writeheader()
        writer.writerows(rows)


def read_groups(path):
    groups = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            groups.setdefault((row["tone"], row["family"]), []).append(row["status"])
    return groups


@pytest.fixture
def filled(tmp_path):
    path = tmp_path / "recs.csv"
    write_csv(path, make_rows())
    call_command("fill_demo_recommendations", "--path", str(path))
    return path


def test_every_group_has_3_to_8_visible_shades(filled):
    for statuses in read_groups(filled).values():
        visible = [s for s in statuses if s in VISIBLE]
        assert 3 <= len(visible) <= 8
        assert len(statuses) == 8


def test_every_group_has_1_to_4_best_shades(filled):
    for statuses in read_groups(filled).values():
        assert 1 <= statuses.count("best") <= 4


def test_only_valid_statuses_are_written(filled):
    for statuses in read_groups(filled).values():
        assert set(statuses) <= VISIBLE | HIDDEN


def test_counts_differ_between_groups(filled):
    counts = {
        sum(1 for s in statuses if s in VISIBLE)
        for statuses in read_groups(filled).values()
    }
    assert len(counts) > 1


def test_same_result_every_run(tmp_path, filled):
    other = tmp_path / "other.csv"
    write_csv(other, make_rows())
    call_command("fill_demo_recommendations", "--path", str(other))
    assert read_groups(filled) == read_groups(other)


def test_running_twice_changes_nothing(filled):
    before = read_groups(filled)
    call_command("fill_demo_recommendations", "--path", str(filled))
    assert read_groups(filled) == before


def test_group_with_your_own_value_is_left_untouched(tmp_path):
    rows = make_rows(tones=2, families=2)
    rows[0]["status"] = "usually_avoid"
    path = tmp_path / "recs.csv"
    write_csv(path, rows)

    call_command("fill_demo_recommendations", "--path", str(path))

    groups = read_groups(path)
    assert groups[("Tone 1", "Family 1")] == ["usually_avoid"] + [""] * 7
    assert all(s != "" for s in groups[("Tone 1", "Family 2")])


def test_group_with_fewer_than_3_shades_stops_the_command(tmp_path):
    path = tmp_path / "recs.csv"
    write_csv(path, make_rows(tones=1, families=1, shades=2))
    with pytest.raises(CommandError, match="Fewer than 3"):
        call_command("fill_demo_recommendations", "--path", str(path))


@pytest.mark.django_db
def test_template_fill_load_gives_a_healthy_varied_catalog(tmp_path):
    tones = [SkinToneFactory() for _ in range(3)]
    families = [ColorFamilyFactory() for _ in range(3)]
    for family in families:
        for _ in range(8):
            ShadeFactory(family=family)
    path = tmp_path / "recs.csv"

    call_command("load_recommendations", "--template", "--path", str(path))
    call_command("fill_demo_recommendations", "--path", str(path))
    call_command("load_recommendations", "--path", str(path))

    assert ShadeRecommendation.objects.count() == 3 * 3 * 8
    assert check_catalog_health().short_shades == []
    for tone in tones:
        for family in families:
            statuses = [r.status for r in get_visible_shades(tone, family)]
            assert 3 <= len(statuses) <= 8
            assert statuses[0] == "best"
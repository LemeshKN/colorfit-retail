"""Seed family-level outfit pairing rules.

Values come from the project owner's hand-made styling table.
They are styling suggestions, not scientific advice. Review them with a
shop owner before real use.

Safe to run twice: rows are matched on family, bottom type and bottom color.
Family rules (top_shade empty) that are not in the table below are deleted,
so every rule ends with exactly the colors listed here.
Shade overrides (top_shade set) are never changed or deleted.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import (
    BottomColor,
    BottomType,
    ColorFamily,
    OutfitPairing,
)

# bottom type slug -> family slug -> bottom colors in rank order (1, 2, 3).
RULES = {
    "jeans": {
        "red": ["Indigo Denim", "Black", "Light Blue Denim"],
        "maroon": ["Indigo Denim", "Black", "Grey"],
        "pink": ["Indigo Denim", "Light Blue Denim", "Black"],
        "orange": ["Indigo Denim", "Black", "Light Blue Denim"],
        "yellow": ["Indigo Denim", "Black", "Light Blue Denim"],
        "green": ["Indigo Denim", "Black", "Light Blue Denim"],
        "blue": ["Indigo Denim", "Black", "Light Blue Denim"],
        "purple": ["Indigo Denim", "Black", "Light Blue Denim"],
        "brown": ["Indigo Denim", "Black", "Light Blue Denim"],
        "neutrals": ["Indigo Denim", "Black", "Light Blue Denim"],
    },
    "trousers": {
        "red": ["Charcoal", "Navy", "Black"],
        "maroon": ["Charcoal", "Navy", "Black"],
        "pink": ["Navy", "Charcoal", "Grey"],
        "orange": ["Charcoal", "Navy", "Brown"],
        "yellow": ["Navy", "Charcoal", "Brown"],
        "green": ["Charcoal", "Navy", "Black"],
        "blue": ["Charcoal", "Grey", "Navy"],
        "purple": ["Charcoal", "Navy", "Black"],
        "brown": ["Charcoal", "Navy", "Black"],
        "neutrals": ["Charcoal", "Navy", "Black"],
    },
    "chinos": {
        "red": ["Khaki", "Beige", "Olive"],
        "maroon": ["Beige", "Khaki", "Off White"],
        "pink": ["Khaki", "Beige", "Olive"],
        "orange": ["Khaki", "Olive", "Beige"],
        "yellow": ["Olive", "Khaki", "Off White"],
        "green": ["Khaki", "Beige", "Tan"],
        "blue": ["Khaki", "Beige", "Off White"],
        "purple": ["Beige", "Khaki", "Olive"],
        "brown": ["Khaki", "Beige", "Off White"],
        "neutrals": ["Khaki", "Olive", "Tan"],
    },
    "pyjama": {
        "red": ["Charcoal", "Black", "Navy"],
        "maroon": ["Black", "Charcoal", "Navy"],
        "pink": ["Charcoal", "Black", "Navy"],
        "orange": ["Charcoal", "Black", "Navy"],
        "yellow": ["Charcoal", "Navy", "Black"],
        "green": ["Charcoal", "Black", "Navy"],
        "blue": ["Navy", "Charcoal", "Black"],
        "purple": ["Black", "Charcoal", "Navy"],
        "brown": ["Off White", "Charcoal", "Black"],
        "neutrals": ["Black", "Charcoal", "Navy"],
    },
}

# Bottom colors that must exist for the table above. Created if missing, so a
# new database works without manual admin steps. Existing colors are not changed.
REQUIRED_COLORS = {"Grey": "#808080", "Tan": "#D2B48C"}


class Command(BaseCommand):
    help = "Seed family-level outfit pairing rules. Safe to run twice."

    def handle(self, *args, **options):
        families = {f.slug: f for f in ColorFamily.objects.all()}
        bottom_types = {b.slug: b for b in BottomType.objects.all()}
        for name, hex_code in REQUIRED_COLORS.items():
            BottomColor.objects.get_or_create(name=name, defaults={"hex": hex_code})
        colors = {c.name: c for c in BottomColor.objects.all()}

        self._check_table(families, bottom_types, colors)

        created = 0
        kept = 0
        removed = 0
        with transaction.atomic():
            for bottom_slug, by_family in RULES.items():
                for family_slug, color_names in by_family.items():
                    family = families[family_slug]
                    bottom = bottom_types[bottom_slug]

                    stale = OutfitPairing.objects.filter(
                        top_family=family,
                        bottom_type=bottom,
                        top_shade__isnull=True,
                    ).exclude(bottom_color__name__in=color_names)
                    removed += stale.count()
                    stale.delete()

                    for rank, color_name in enumerate(color_names, start=1):
                        _, was_created = OutfitPairing.objects.update_or_create(
                            top_family=family,
                            top_shade=None,
                            bottom_type=bottom,
                            bottom_color=colors[color_name],
                            defaults={"rank": rank},
                        )
                        if was_created:
                            created += 1
                        else:
                            kept += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Pairing rules done. Created {created}, already present {kept}, "
                f"removed {removed}."
            )
        )

    def _check_table(self, families, bottom_types, colors):
        missing = []
        repeated = []
        for bottom_slug, by_family in RULES.items():
            if bottom_slug not in bottom_types:
                missing.append(f"bottom type '{bottom_slug}'")
            for family_slug, color_names in by_family.items():
                if family_slug not in families:
                    missing.append(f"family '{family_slug}'")
                if len(set(color_names)) != len(color_names):
                    repeated.append(f"{bottom_slug}/{family_slug}")
                for name in color_names:
                    if name not in colors:
                        missing.append(f"bottom color '{name}'")
        if missing:
            raise CommandError(
                "Missing in the database: " + ", ".join(sorted(set(missing)))
            )
        if repeated:
            raise CommandError(
                "Same color listed twice in: " + ", ".join(sorted(repeated))
            )
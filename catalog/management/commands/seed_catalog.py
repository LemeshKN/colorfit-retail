from django.core.management.base import BaseCommand
from django.db import transaction

from catalog import seed_data as d
from catalog.models import (
    BottomColor,
    BottomType,
    CardCode,
    ColorFamily,
    GarmentType,
    Shade,
    SkinTone,
)
from shops.models import Shop


class Command(BaseCommand):
    help = "Load sample catalog data. Safe to run again."

    @transaction.atomic
    def handle(self, *args, **options):
        tones = {}
        for label in d.TONES:
            tones[label], _ = SkinTone.objects.get_or_create(label=label)

        # get_or_create so a rerun does not undo changes made in admin
        for code, number in d.CARDS.items():
            CardCode.objects.get_or_create(
                code=code, defaults={"skin_tone": tones[f"Tone {number}"]}
            )

        for order, (name, slug) in enumerate(d.FAMILIES, start=1):
            family, _ = ColorFamily.objects.update_or_create(
                slug=slug, defaults={"name": name, "sort_order": order}
            )
            for shade_name, hex_value in d.SHADES[name]:
                Shade.objects.update_or_create(
                    family=family, name=shade_name, defaults={"hex": hex_value}
                )

        bottom_types = {}
        for name, slug in d.BOTTOM_TYPES:
            bottom_types[slug], _ = BottomType.objects.update_or_create(
                slug=slug, defaults={"name": name}
            )

        for name, hex_value in d.BOTTOM_COLORS:
            BottomColor.objects.update_or_create(
                name=name, defaults={"hex": hex_value}
            )

        for name, slug, has_pairing in d.GARMENTS:
            garment, _ = GarmentType.objects.update_or_create(
                slug=slug, defaults={"name": name, "has_pairing": has_pairing}
            )
            wanted = d.GARMENT_BOTTOMS.get(slug, [])
            garment.bottom_types.set([bottom_types[s] for s in wanted])

        Shop.objects.get_or_create(
            code=d.DEMO_SHOP["code"], defaults=d.DEMO_SHOP
        )

        self.stdout.write(self.style.SUCCESS("Catalog seeded."))
        self.stdout.write(
            f"Tones: {SkinTone.objects.count()}, cards: {CardCode.objects.count()}, "
            f"families: {ColorFamily.objects.count()}, shades: {Shade.objects.count()}"
        )
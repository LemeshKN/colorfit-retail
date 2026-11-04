from django.core.management.base import BaseCommand

from sunglasses.models import FaceShapeRule

STARTING_SHAPES = [
    # name, slug, sort_order, length, forehead, jaw
    ("Oval", "oval", 1, 1.21, 0.85, 0.79),
    ("Square", "square", 2, 1.20, 0.84, 0.82),
    ("Round", "round", 3, 1.11, 0.84, 0.80),
    ("Heart", "heart", 4, 1.24, 0.86, 0.79),
    ("Oblong", "oblong", 5, 1.24, 0.85, 0.81),
    ("Diamond", "diamond", 6, 1.19, 0.86, 0.82),
]


class Command(BaseCommand):
    help = "Create the six face shapes. Use --overwrite to reset the ratios."

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        changed = 0
        for name, slug, order, length, forehead, jaw in STARTING_SHAPES:
            values = {
                "name": name,
                "sort_order": order,
                "length_ratio": length,
                "forehead_ratio": forehead,
                "jaw_ratio": jaw,
            }
            if options["overwrite"]:
                _, did_change = FaceShapeRule.objects.update_or_create(
                    slug=slug, defaults=values
                )
            else:
                _, did_change = FaceShapeRule.objects.get_or_create(
                    slug=slug, defaults=values
                )
            changed += int(did_change)
        self.stdout.write(f"Created {changed} face shapes.")
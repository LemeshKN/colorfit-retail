from django.core.management.base import BaseCommand

from sunglasses.models import FaceShapeRule

# Starting guesses, written by me from general ideas about face shapes.
# They are NOT measured values. Tune them in admin on real photos.
STARTING_SHAPES = [
    # name, slug, sort_order, length, forehead, jaw
    ("Oval", "oval", 1, 1.45, 0.85, 0.75),
    ("Square", "square", 2, 1.20, 0.90, 0.90),
    ("Round", "round", 3, 1.15, 0.88, 0.80),
    ("Heart", "heart", 4, 1.35, 0.95, 0.62),
    ("Oblong", "oblong", 5, 1.65, 0.88, 0.85),
    ("Diamond", "diamond", 6, 1.40, 0.75, 0.72),
]


class Command(BaseCommand):
    help = "Create the six face shapes with starting ratios. Never changes a shape that exists."

    def handle(self, *args, **options):
        created = 0
        for name, slug, order, length, forehead, jaw in STARTING_SHAPES:
            _, was_created = FaceShapeRule.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "sort_order": order,
                    "length_ratio": length,
                    "forehead_ratio": forehead,
                    "jaw_ratio": jaw,
                },
            )
            created += int(was_created)
        self.stdout.write(f"Created {created} face shapes. Existing ones were not changed.")
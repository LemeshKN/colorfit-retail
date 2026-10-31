from django.core.management.base import BaseCommand, CommandError

from sunglasses.models import FaceShapeRule, FrameStyle

# What the lens looks like. Staff and customers can use these words in the shop.
FRAME_LOOK = {
    "teardrop": "Wider at the top, narrower at the bottom",
    "classic-square": "Square lenses with softly rounded corners",
    "rectangular": "Wide, slim lenses",
    "round": "Circular lenses",
    "oval": "Soft, rounded lenses",
    "square": "Boxy lenses with sharp corners",
    "oversized": "Large lenses with extra coverage",
    "browline": "Thick top bar, lighter lower edge",
}

# Starting list. You curate the final choices. These are styling suggestions only.
STARTING_FRAMES = {
    "oval": [
        ("Teardrop", "teardrop"),
        ("Classic square", "classic-square"),
        ("Rectangular", "rectangular"),
    ],
    "square": [("Round", "round"), ("Teardrop", "teardrop"), ("Oval", "oval")],
    "round": [
        ("Rectangular", "rectangular"),
        ("Classic square", "classic-square"),
        ("Square", "square"),
    ],
    "heart": [("Teardrop", "teardrop"), ("Round", "round"), ("Oval", "oval")],
    "oblong": [
        ("Oversized", "oversized"),
        ("Classic square", "classic-square"),
        ("Round", "round"),
    ],
    "diamond": [("Teardrop", "teardrop"), ("Oval", "oval"), ("Browline", "browline")],
}


class Command(BaseCommand):
    help = "Create three frame styles for each face shape. Never changes a row that exists."

    def handle(self, *args, **options):
        created = 0
        for shape_slug, frames in STARTING_FRAMES.items():
            shape = FaceShapeRule.objects.filter(slug=shape_slug).first()
            if shape is None:
                raise CommandError(
                    f"Face shape '{shape_slug}' is missing. Run seed_face_shapes first."
                )
            for rank, (name, slug) in enumerate(frames, start=1):
                _, was_created = FrameStyle.objects.get_or_create(
                    shape=shape,
                    rank=rank,
                    defaults={
                        "name": name,
                        "slug": slug,
                        "image_file": f"img/frames/{slug}.svg",
                        "note": FRAME_LOOK[slug],
                    },
                )
                created += int(was_created)
        self.stdout.write(f"Created {created} frame styles. Existing ones were not changed.")
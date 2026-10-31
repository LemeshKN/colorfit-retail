from django.core.management.base import BaseCommand, CommandError

from sunglasses.models import FaceShapeRule, FrameStyle

# Starting list. You curate the final choices. These are styling suggestions only.
STARTING_FRAMES = {
    "oval": [
        ("Teardrop", "teardrop", "Soft curves that sit well on balanced proportions."),
        ("Classic square", "classic-square", "A clean shape that keeps the look simple."),
        ("Rectangular", "rectangular", "A slim shape that adds a little structure."),
    ],
    "square": [
        ("Round", "round", "Round lenses soften strong lines."),
        ("Teardrop", "teardrop", "A gentle curve that balances a straight jaw."),
        ("Oval", "oval", "A soft shape that eases angles."),
    ],
    "round": [
        ("Rectangular", "rectangular", "Straight lines add contrast to soft curves."),
        ("Classic square", "classic-square", "Defined corners add structure."),
        ("Square", "square", "Sharp corners give a crisp look."),
    ],
    "heart": [
        ("Teardrop", "teardrop", "A wider top is balanced by a narrower bottom."),
        ("Round", "round", "Soft curves keep the look gentle."),
        ("Oval", "oval", "A smooth shape that suits a narrower chin."),
    ],
    "oblong": [
        ("Oversized", "oversized", "Larger lenses add width to a longer face."),
        ("Classic square", "classic-square", "A deeper frame balances length."),
        ("Round", "round", "Round lenses add softness."),
    ],
    "diamond": [
        ("Teardrop", "teardrop", "A gentle curve that balances a narrower forehead and chin."),
        ("Oval", "oval", "Soft curves ease strong cheekbones."),
        ("Browline", "browline", "A strong top line balances a narrower forehead."),
    ],
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
            for rank, (name, slug, note) in enumerate(frames, start=1):
                _, was_created = FrameStyle.objects.get_or_create(
                    shape=shape,
                    rank=rank,
                    defaults={
                        "name": name,
                        "slug": slug,
                        "image_file": f"img/frames/{slug}.svg",
                        "note": note,
                    },
                )
                created += int(was_created)
        self.stdout.write(f"Created {created} frame styles. Existing ones were not changed.")
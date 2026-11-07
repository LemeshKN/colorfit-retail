from django.core.management.base import BaseCommand

from sunglasses.services import apply_shape_image_urls, apply_tryon_urls
from sunglasses.shape_image_urls import SHAPE_IMAGE_URLS
from sunglasses.tryon_urls import TRYON_URLS


class Command(BaseCommand):
    help = "Set Cloudinary links for try-on frames and face shape pictures."

    def handle(self, *args, **options):
        for label, counts in (
            ("frame", apply_tryon_urls(TRYON_URLS)),
            ("shape", apply_shape_image_urls(SHAPE_IMAGE_URLS)),
        ):
            for slug, count in counts.items():
                if count:
                    self.stdout.write(f"{label} {slug}: {count} row(s) updated")
                else:
                    self.stderr.write(f"{label} {slug}: no row has this slug")
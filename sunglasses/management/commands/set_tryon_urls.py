from django.core.management.base import BaseCommand

from sunglasses.services import apply_tryon_urls
from sunglasses.tryon_urls import TRYON_URLS


class Command(BaseCommand):
    help = "Set the try-on image link on every frame style, matched by slug."

    def handle(self, *args, **options):
        for slug, count in apply_tryon_urls(TRYON_URLS).items():
            if count:
                self.stdout.write(f"{slug}: {count} row(s) updated")
            else:
                self.stderr.write(f"{slug}: no frame style has this slug")

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Shade, ShadeRecommendation, SkinTone

DEFAULT_PATH = Path(settings.BASE_DIR) / "catalog" / "seed" / "recommendations.csv"
VALID_STATUSES = {s.value for s in ShadeRecommendation.Status}


class Command(BaseCommand):
    help = "Write a blank recommendations CSV (--template) or load a filled one."

    def add_arguments(self, parser):
        parser.add_argument("--template", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--path", default=str(DEFAULT_PATH))

    def handle(self, *args, **options):
        path = Path(options["path"])
        if options["template"]:
            self.write_template(path, options["force"])
        else:
            self.load(path)

    def write_template(self, path, force):
        if path.exists() and not force:
            raise CommandError(f"{path} exists. Use --force to overwrite it.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tone", "family", "shade", "status"])
            shades = Shade.objects.select_related("family")
            for tone in SkinTone.objects.all():
                for shade in shades:
                    writer.writerow([tone.label, shade.family.name, shade.name, ""])
        self.stdout.write(self.style.SUCCESS(f"Template written: {path}"))
        self.stdout.write("Fill the status column with: best, good, try_carefully, usually_avoid")

    @transaction.atomic
    def load(self, path):
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        tones = {t.label: t for t in SkinTone.objects.all()}
        shades = {
            (s.family.name, s.name): s for s in Shade.objects.select_related("family")
        }
        errors, ready, skipped = [], [], 0

        with path.open(newline="", encoding="utf-8") as f:
            for line_no, row in enumerate(csv.DictReader(f), start=2):
                status = row["status"].strip().lower()
                if not status:
                    skipped += 1
                    continue
                tone = tones.get(row["tone"].strip())
                shade = shades.get((row["family"].strip(), row["shade"].strip()))
                if tone is None or shade is None:
                    errors.append(f"Line {line_no}: unknown tone or shade.")
                elif status not in VALID_STATUSES:
                    errors.append(f"Line {line_no}: bad status '{status}'.")
                else:
                    ready.append((tone, shade, status))

        if errors:
            raise CommandError("Nothing loaded.\n" + "\n".join(errors[:20]))

        for tone, shade, status in ready:
            ShadeRecommendation.objects.update_or_create(
                skin_tone=tone, shade=shade, defaults={"status": status}
            )
        self.stdout.write(
            self.style.SUCCESS(f"Loaded {len(ready)} rows. Skipped {skipped} blank rows.")
        )
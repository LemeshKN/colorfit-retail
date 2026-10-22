import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_PATH = Path(settings.BASE_DIR) / "catalog" / "seed" / "recommendations.csv"

# Placeholder pattern for 8 shades. Not real styling advice.
PATTERN = [
    "best", "best", "good", "good",
    "good", "try_carefully", "usually_avoid", "usually_avoid",
]


class Command(BaseCommand):
    help = "Fill blank status cells with a DEMO pattern for development only."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(DEFAULT_PATH))

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError("Run load_recommendations --template first.")

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # Group rows by (tone, family), keeping CSV order.
        groups = {}
        family_order = []
        for row in rows:
            if row["family"] not in family_order:
                family_order.append(row["family"])
            groups.setdefault((row["tone"], row["family"]), []).append(row)

        for (tone, family), group in groups.items():
            tone_no = int(tone.split()[1])
            family_no = family_order.index(family)
            offset = (tone_no + family_no) % len(group)
            for position, row in enumerate(group):
                if row["status"].strip():
                    continue  # never overwrite your own values
                row["status"] = PATTERN[(position - offset) % len(PATTERN)]

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tone", "family", "shade", "status"])
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.WARNING("Demo values written. Placeholder only."))
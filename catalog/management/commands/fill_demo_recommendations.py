"""DEMO ONLY. Fill blank status cells in the recommendations CSV.

All values are placeholders so you can show a shop owner that different
card IDs give different styling suggestions. Replace them with real
curated values before a real shop uses the app.

For each tone and color family, the command picks:
- 3 to 8 visible shades (best or good),
- 1 to 4 of the visible shades as "best", the rest as "good",
- a hidden status for every other shade (never shown to customers).

The choice uses a fixed seed built from the tone and family, so every run
gives the same result. A group (one tone and one family) that already has
any filled status is left untouched, so your own values are never changed.
"""

import csv
import random
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_PATH = Path(settings.BASE_DIR) / "catalog" / "seed" / "recommendations.csv"

MIN_VISIBLE = 3
MAX_BEST = 4
HIDDEN = ["try_carefully", "usually_avoid"]


def plan_group(tone, family, size):
    """Return one status per shade position, the same on every run."""
    rng = random.Random(f"{tone}|{family}")
    visible = rng.randint(MIN_VISIBLE, size)
    best = rng.randint(1, min(MAX_BEST, visible - 1))
    order = list(range(size))
    rng.shuffle(order)

    statuses = [""] * size
    for rank, position in enumerate(order):
        if rank < best:
            statuses[position] = "best"
        elif rank < visible:
            statuses[position] = "good"
        else:
            statuses[position] = HIDDEN[(rank - visible) % 2]
    return statuses


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

        groups = {}
        for row in rows:
            groups.setdefault((row["tone"], row["family"]), []).append(row)

        short = [
            f"{tone} / {family}"
            for (tone, family), group in groups.items()
            if len(group) < MIN_VISIBLE
        ]
        if short:
            raise CommandError(
                f"Fewer than {MIN_VISIBLE} shades in: " + ", ".join(short[:10])
            )

        filled = skipped = 0
        summary = {}
        for (tone, family), group in groups.items():
            if any(row["status"].strip() for row in group):
                skipped += 1  # keep your own values
                continue
            statuses = plan_group(tone, family, len(group))
            for row, status in zip(group, statuses):
                row["status"] = status
            visible = sum(1 for s in statuses if s in ("best", "good"))
            best = statuses.count("best")
            summary.setdefault(tone, []).append(f"{visible}({best})")
            filled += 1

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tone", "family", "shade", "status"])
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write("Visible shades per family, with best count in brackets:")
        for tone, cells in summary.items():
            self.stdout.write(f"{tone}: " + " ".join(cells))
        self.stdout.write(
            self.style.WARNING(
                f"Demo values written for {filled} groups, left {skipped} untouched. "
                "Placeholder only."
            )
        )
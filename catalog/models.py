from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

hex_validator = RegexValidator(
    r"^#[0-9A-Fa-f]{6}$", "Use a hex color like #800000."
)
tone_label_validator = RegexValidator(
    r"^Tone \d{1,2}$", 'Use a neutral label like "Tone 4".'
)
card_code_validator = RegexValidator(
    r"^ST-\d{2}$", 'Use the format "ST-07".'
)


class SkinTone(models.Model):
    # Neutral label only. Ordered by id because "Tone 10" sorts before "Tone 2" as text.
    label = models.CharField(
        max_length=10, unique=True, validators=[tone_label_validator]
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.label


class CardCode(models.Model):
    code = models.CharField(
        max_length=10, unique=True, validators=[card_code_validator]
    )
    skin_tone = models.ForeignKey(
        SkinTone, on_delete=models.PROTECT, related_name="card_codes"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class ColorFamily(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "color families"

    def __str__(self):
        return self.name


class Shade(models.Model):
    family = models.ForeignKey(
        ColorFamily, on_delete=models.CASCADE, related_name="shades"
    )
    name = models.CharField(max_length=60)
    hex = models.CharField(max_length=7, validators=[hex_validator])

    class Meta:
        ordering = ["family__sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["family", "name"], name="unique_shade_name_per_family"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.family.name})"


class BottomType(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class BottomColor(models.Model):
    name = models.CharField(max_length=40, unique=True)
    hex = models.CharField(max_length=7, validators=[hex_validator])

    def __str__(self):
        return self.name


class GarmentType(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True)
    has_pairing = models.BooleanField(default=False)
    # Added to the locked model: which bottom types this garment can pair with.
    bottom_types = models.ManyToManyField(
        BottomType, blank=True, related_name="garments"
    )

    def __str__(self):
        return self.name


class ShadeRecommendation(models.Model):
    class Status(models.TextChoices):
        BEST = "best", "Best for you"
        GOOD = "good", "Good option"
        TRY_CAREFULLY = "try_carefully", "Try carefully (never shown)"
        USUALLY_AVOID = "usually_avoid", "Usually avoid (never shown)"

    # A styling suggestion entered by hand. Depends on tone and shade only.
    skin_tone = models.ForeignKey(
        SkinTone, on_delete=models.CASCADE, related_name="recommendations"
    )
    shade = models.ForeignKey(
        Shade, on_delete=models.CASCADE, related_name="recommendations"
    )
    status = models.CharField(max_length=20, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["skin_tone", "shade"], name="unique_recommendation"
            )
        ]

    def __str__(self):
        return f"{self.skin_tone} / {self.shade.name}: {self.status}"


class OutfitPairing(models.Model):
    # Family rule: top_shade is empty.
    # Shade override: top_shade is set, only when one shade breaks the family rule.
    top_family = models.ForeignKey(
        ColorFamily, on_delete=models.CASCADE, related_name="pairings"
    )
    top_shade = models.ForeignKey(
        Shade,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="pairing_overrides",
    )
    bottom_type = models.ForeignKey(BottomType, on_delete=models.CASCADE)
    bottom_color = models.ForeignKey(BottomColor, on_delete=models.CASCADE)
    rank = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["top_family", "bottom_type", "bottom_color"],
                condition=Q(top_shade__isnull=True),
                name="unique_family_pairing",
            ),
            models.UniqueConstraint(
                fields=["top_family", "top_shade", "bottom_type", "bottom_color"],
                condition=Q(top_shade__isnull=False),
                name="unique_shade_override",
            ),
        ]

    def clean(self):
        if self.top_shade_id and self.top_shade.family_id != self.top_family_id:
            raise ValidationError(
                {"top_shade": "This shade is not in the chosen top family."}
            )

    def __str__(self):
        return f"{self.top_family} + {self.bottom_type} {self.bottom_color} (rank {self.rank})"
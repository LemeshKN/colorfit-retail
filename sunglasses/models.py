from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import validate_cloudinary_url

RATIO_RULES = [MinValueValidator(0.1), MaxValueValidator(5)]


class FaceShapeRule(models.Model):
    """One face shape and the three ratios that describe it.

    Ratios are measured against cheekbone width, so they have no unit.
    The numbers are tuned by hand on real photos. They are styling rules,
    not scientific values.
    """

    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    length_ratio = models.FloatField(
        validators=RATIO_RULES, help_text="Face length divided by cheekbone width."
    )
    forehead_ratio = models.FloatField(
        validators=RATIO_RULES, help_text="Forehead width divided by cheekbone width."
    )
    jaw_ratio = models.FloatField(
        validators=RATIO_RULES, help_text="Jaw width divided by cheekbone width."
    )
    is_active = models.BooleanField(default=True)
        
    image_url = models.URLField(
        max_length=300,
        blank=True,
        validators=[validate_cloudinary_url],
        help_text="Cloudinary picture of this face shape. "
        "Leave empty to use the built-in drawing.",
    )

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class FrameStyle(models.Model):
    """A curated frame style shown for one face shape."""

    shape = models.ForeignKey(
        FaceShapeRule, on_delete=models.CASCADE, related_name="frame_styles"
    )
    name = models.CharField(max_length=60)
    slug = models.SlugField()
    image_file = models.CharField(
        max_length=120,
        help_text="Path inside the static folder, for example img/frames/aviator.svg",
    )
    note = models.CharField(
        max_length=200, help_text="One short styling note. No accuracy claims."
    )
    rank = models.PositiveSmallIntegerField(
        default=1, help_text="1 is shown first."
    )

    tryon_image_url = models.URLField(
        max_length=300,
        blank=True,
        validators=[validate_cloudinary_url],
        help_text="Transparent PNG on Cloudinary for the live try-on. "
        "Leave empty to hide the try-on for this frame.",
    )
    tryon_width_factor = models.FloatField(
        default=1.6,
        validators=[MinValueValidator(0.8), MaxValueValidator(3)],
        help_text="Frame width divided by the distance between the outer eye "
        "corners. Tune it on a real phone.",
    )

    class Meta:
        ordering = ["shape", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["shape", "slug"], name="unique_frame_slug_per_shape"
            ),
            models.UniqueConstraint(
                fields=["shape", "rank"], name="unique_frame_rank_per_shape"
            ),
        ]

    def __str__(self):
        return f"{self.shape.name}: {self.name}"
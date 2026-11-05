from urllib.parse import urlparse

from django.core.exceptions import ValidationError


def validate_cloudinary_url(value):
    """Only allow https links on Cloudinary's image host."""
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com":
        raise ValidationError("Use an https://res.cloudinary.com/ link.")

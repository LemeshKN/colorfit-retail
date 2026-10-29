from django.db import models


class Shop(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # for example SH-014
    slug = models.SlugField(unique=True)  # for example sh-014
    city = models.CharField(max_length=60)
    is_active = models.BooleanField(default=True)
    access_key_hash = models.CharField(max_length=128, blank=True)  # hashed, never plain text

    def __str__(self):
        return f"{self.name} ({self.code})"


class AdviceSession(models.Model):
    # One row per valid card entry. Never created on page load.
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="sessions")
    card_code = models.ForeignKey("catalog.CardCode", on_delete=models.PROTECT)
    garment = models.ForeignKey(
        "catalog.GarmentType", null=True, blank=True, on_delete=models.PROTECT
    )
    device_id = models.UUIDField()
    local_date = models.DateField()  # India date, set by the service
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["shop", "local_date"])]

    def __str__(self):
        return f"{self.shop.code} {self.local_date} {self.card_code}"
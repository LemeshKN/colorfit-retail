import uuid

import factory
from django.utils import timezone

from catalog.tests.factories import CardCodeFactory
from shops import models


class ShopFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Shop

    name = factory.Sequence(lambda n: f"Shop {n}")
    code = factory.Sequence(lambda n: f"SH-{n + 1:03d}")
    slug = factory.Sequence(lambda n: f"sh-{n + 1:03d}")
    city = "Raipur"
    is_active = True


class AdviceSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AdviceSession

    shop = factory.SubFactory(ShopFactory)
    card_code = factory.SubFactory(CardCodeFactory)
    garment = None
    device_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    local_date = factory.LazyFunction(timezone.localdate)
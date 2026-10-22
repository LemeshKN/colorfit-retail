import factory

from catalog import models


class SkinToneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.SkinTone

    label = factory.Sequence(lambda n: f"Tone {n + 1}")


class CardCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CardCode

    code = factory.Sequence(lambda n: f"ST-{n + 1:02d}")
    skin_tone = factory.SubFactory(SkinToneFactory)
    is_active = True


class ColorFamilyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ColorFamily

    name = factory.Sequence(lambda n: f"Family {n}")
    slug = factory.Sequence(lambda n: f"family-{n}")
    sort_order = factory.Sequence(int)


class ShadeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Shade

    family = factory.SubFactory(ColorFamilyFactory)
    name = factory.Sequence(lambda n: f"Shade {n}")
    hex = "#800000"


class BottomTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.BottomType

    name = factory.Sequence(lambda n: f"Bottom {n}")
    slug = factory.Sequence(lambda n: f"bottom-{n}")


class BottomColorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.BottomColor

    name = factory.Sequence(lambda n: f"Bottom color {n}")
    hex = "#1F2937"


class GarmentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GarmentType

    name = factory.Sequence(lambda n: f"Garment {n}")
    slug = factory.Sequence(lambda n: f"garment-{n}")
    has_pairing = False


class ShadeRecommendationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ShadeRecommendation

    skin_tone = factory.SubFactory(SkinToneFactory)
    shade = factory.SubFactory(ShadeFactory)
    status = "best"


class OutfitPairingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.OutfitPairing

    top_family = factory.SubFactory(ColorFamilyFactory)
    top_shade = None
    bottom_type = factory.SubFactory(BottomTypeFactory)
    bottom_color = factory.SubFactory(BottomColorFactory)
    rank = 1
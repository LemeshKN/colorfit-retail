from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BottomColor,
    BottomType,
    CardCode,
    ColorFamily,
    GarmentType,
    OutfitPairing,
    Shade,
    ShadeRecommendation,
    SkinTone,
)


def swatch(hex_value):
    return format_html(
        '<span style="display:inline-block;width:28px;height:16px;'
        'border:1px solid #888;background:{}"></span> {}',
        hex_value,
        hex_value,
    )


@admin.register(SkinTone)
class SkinToneAdmin(admin.ModelAdmin):
    list_display = ["label"]


@admin.register(CardCode)
class CardCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "skin_tone", "is_active"]
    list_filter = ["skin_tone", "is_active"]
    search_fields = ["code"]


class ShadeInline(admin.TabularInline):
    model = Shade
    extra = 0


@admin.register(ColorFamily)
class ColorFamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "sort_order"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ShadeInline]


@admin.register(Shade)
class ShadeAdmin(admin.ModelAdmin):
    list_display = ["name", "family", "color"]
    list_filter = ["family"]
    search_fields = ["name"]

    @admin.display(description="Color")
    def color(self, obj):
        return swatch(obj.hex)


@admin.register(BottomType)
class BottomTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BottomColor)
class BottomColorAdmin(admin.ModelAdmin):
    list_display = ["name", "color"]

    @admin.display(description="Color")
    def color(self, obj):
        return swatch(obj.hex)


@admin.register(GarmentType)
class GarmentTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "has_pairing"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["bottom_types"]


@admin.register(ShadeRecommendation)
class ShadeRecommendationAdmin(admin.ModelAdmin):
    list_display = ["skin_tone", "shade", "status"]
    list_editable = ["status"]
    list_filter = ["skin_tone", "shade__family", "status"]
    list_select_related = ["skin_tone", "shade", "shade__family"]
    autocomplete_fields = ["shade"]
    list_per_page = 100


@admin.register(OutfitPairing)
class OutfitPairingAdmin(admin.ModelAdmin):
    list_display = ["top_family", "top_shade", "bottom_type", "bottom_color", "rank"]
    list_filter = ["top_family", "bottom_type"]
    autocomplete_fields = ["top_shade"]
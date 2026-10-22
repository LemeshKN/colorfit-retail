from django.contrib import admin
from django.utils.html import format_html
from django.contrib import admin, messages

from .services import check_catalog_health

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


@admin.action(description="Check catalog health")
def run_catalog_health_check(modeladmin, request, queryset):
    report = check_catalog_health()
    if report.is_ok:
        modeladmin.message_user(
            request, "Catalog health: all checks passed.", messages.SUCCESS
        )
        return

    for item in report.short_shades[:10]:
        modeladmin.message_user(
            request,
            f"{item['tone']} + {item['family']} has {item['visible']} visible "
            f"shades. It needs at least 3.",
            messages.ERROR,
        )
    if len(report.short_shades) > 10:
        modeladmin.message_user(
            request,
            f"{len(report.short_shades) - 10} more combinations have fewer "
            f"than 3 visible shades.",
            messages.ERROR,
        )
    if report.missing_pairings:
        sample = report.missing_pairings[0]
        modeladmin.message_user(
            request,
            f"{len(report.missing_pairings)} family and bottom type "
            f"combinations have no pairing rule. Example: "
            f"{sample['family']} + {sample['bottom_type']}.",
            messages.WARNING,
        )

@admin.register(ColorFamily)
class ColorFamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "sort_order"]
    actions = [run_catalog_health_check]
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
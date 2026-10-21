from django.contrib import admin

from .models import AdviceSession, Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "city", "is_active"]
    list_filter = ["city", "is_active"]
    prepopulated_fields = {"slug": ("code",)}  # SH-014 becomes sh-014


@admin.register(AdviceSession)
class AdviceSessionAdmin(admin.ModelAdmin):
    list_display = ["shop", "local_date", "card_code", "garment", "created_at"]
    list_filter = ["shop", "local_date"]

    # Visit records are written by the app only. Nobody edits them by hand.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
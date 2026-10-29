from datetime import timedelta

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from .models import AdviceSession, Shop
from .services import (
    KEY_MIN_LENGTH,
    set_shop_key,
    shop_needs_key,
    unique_visits_report,
)


class ReportFilterForm(forms.Form):
    shop = forms.ModelChoiceField(queryset=Shop.objects.all())
    start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["end"] < data["start"]:
            raise forms.ValidationError("End date must be on or after start date.")
        return data

class ShopAdminForm(forms.ModelForm):
    new_pass_key = forms.CharField(
        label="New pass key",
        required=False,
        widget=forms.PasswordInput(
            render_value=False, attrs={"autocomplete": "new-password"}
        ),
        help_text=f"At least {KEY_MIN_LENGTH} characters. Leave blank to keep the current key.",
    )
    remove_pass_key = forms.BooleanField(
        label="Remove the pass key",
        required=False,
        help_text="Tick this to let customers in without a key.",
    )

    class Meta:
        model = Shop
        exclude = ["access_key_hash"]

    def clean_new_pass_key(self):
        key = (self.cleaned_data.get("new_pass_key") or "").strip()
        if key and len(key) < KEY_MIN_LENGTH:
            raise forms.ValidationError(
                f"The key needs at least {KEY_MIN_LENGTH} characters."
            )
        return key

    def clean(self):
        data = super().clean()
        if data.get("new_pass_key") and data.get("remove_pass_key"):
            raise forms.ValidationError("Type a new key or tick remove, not both.")
        return data


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    form = ShopAdminForm
    list_display = ["name", "code", "city", "is_active", "has_pass_key"]
    list_filter = ["city", "is_active"]
    prepopulated_fields = {"slug": ("code",)}  # SH-014 becomes sh-014

    @admin.display(boolean=True, description="Pass key set")
    def has_pass_key(self, obj):
        return shop_needs_key(obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get("remove_pass_key"):
            set_shop_key(obj, "")
        elif form.cleaned_data.get("new_pass_key"):
            set_shop_key(obj, form.cleaned_data["new_pass_key"])

@admin.register(AdviceSession)
class AdviceSessionAdmin(admin.ModelAdmin):
    list_display = ["shop", "local_date", "card_code", "garment", "created_at"]
    list_filter = ["shop", "local_date"]

    def get_urls(self):
        custom = [
            path(
                "report/",
                self.admin_site.admin_view(self.report_view),
                name="shops_advicesession_report",
            )
        ]
        return custom + super().get_urls()

    def report_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        today = timezone.localdate()
        form = ReportFilterForm(
            request.GET or None,
            initial={"start": today - timedelta(days=6), "end": today},
        )
        report = None
        if form.is_valid():
            report = unique_visits_report(
                form.cleaned_data["shop"],
                (form.cleaned_data["start"], form.cleaned_data["end"]),
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Visit report",
            "opts": self.model._meta,
            "form": form,
            "report": report,
        }
        return TemplateResponse(
            request, "admin/shops/advicesession/report.html", context
        )

    # Visit records are written by the app only. Nobody edits them by hand.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
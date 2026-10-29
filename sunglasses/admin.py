from django.contrib import admin, messages
from django.db.models import Count

from .models import FaceShapeRule, FrameStyle
from .services import EXPECTED_SHAPES, FRAMES_PER_SHAPE, check_sunglasses_health


class FrameStyleInline(admin.TabularInline):
    model = FrameStyle
    extra = 0
    max_num = FRAMES_PER_SHAPE
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FaceShapeRule)
class FaceShapeRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "frame_count", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [FrameStyleInline]
    actions = ["run_health_check"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_frames=Count("frame_styles"))

    @admin.display(description="Frame styles", ordering="n_frames")
    def frame_count(self, obj):
        return obj.n_frames

    @admin.action(description="Check that every shape has its frame styles")
    def run_health_check(self, request, queryset):
        report = check_sunglasses_health()
        if report.is_ok:
            self.message_user(
                request,
                f"All {EXPECTED_SHAPES} face shapes have {FRAMES_PER_SHAPE} frame styles.",
            )
            return
        if report.shape_count is not None:
            self.message_user(
                request,
                f"Expected {EXPECTED_SHAPES} active face shapes, found {report.shape_count}.",
                level=messages.WARNING,
            )
        for row in report.short_shapes:
            self.message_user(
                request,
                f"{row['shape'].name} has {row['frames']} of {FRAMES_PER_SHAPE} frame styles.",
                level=messages.WARNING,
            )


@admin.register(FrameStyle)
class FrameStyleAdmin(admin.ModelAdmin):
    list_display = ["name", "shape", "rank", "image_file"]
    list_filter = ["shape"]
    prepopulated_fields = {"slug": ("name",)}
from django.urls import path

from . import views

app_name = "advisor"

urlpatterns = [
    path("", views.find_shop, name="find_shop"),
    path("s/<slug:shop_slug>/", views.card_entry, name="card_entry"),
    path("s/<slug:shop_slug>/garments/", views.garments, name="garments"),
    path(
        "s/<slug:shop_slug>/colors/<slug:garment_slug>/",
        views.colors,
        name="colors",
    ),
    path(
        "s/<slug:shop_slug>/shades/<slug:garment_slug>/<slug:family_slug>/",
        views.shades,
        name="shades",
    ),
    path(
        "s/<slug:shop_slug>/pairing/<slug:garment_slug>/<int:shade_id>/",
        views.pairing_bottoms,
        name="pairing_bottoms",
    ),
    path(
        "s/<slug:shop_slug>/pairing/<slug:garment_slug>/<int:shade_id>/<slug:bottom_slug>/",
        views.pairing,
        name="pairing",
    ),
]
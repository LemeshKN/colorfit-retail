from django.urls import path

from . import views

app_name = "sunglasses"

urlpatterns = [
    path("s/<slug:shop_slug>/sunglasses/", views.intro, name="intro"),
    path("s/<slug:shop_slug>/sunglasses/shapes/", views.shapes, name="shapes"),
    path(
        "s/<slug:shop_slug>/sunglasses/shape/<slug:shape_slug>/",
        views.shape_detail,
        name="shape_detail",
    ),
    path("s/<slug:shop_slug>/sunglasses/unclear/", views.unclear, name="unclear"),
]
from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("garments/", views.GarmentListView.as_view(), name="garments"),
    path("families/", views.FamilyListView.as_view(), name="families"),
    path("cards/resolve/", views.CardResolveView.as_view(), name="card_resolve"),
    path("shades/", views.ShadeListView.as_view(), name="shades"),
    path("pairings/", views.PairingListView.as_view(), name="pairings"),
]
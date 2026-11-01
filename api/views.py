from django.conf import settings
from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from catalog.services import (
    InvalidCardError,
    get_bottom_type,
    get_family,
    get_pairings,
    get_shade,
    get_visible_shades,
    list_families,
    list_garments,
    resolve_card,
)
from sunglasses.services import (
    InvalidMeasurementError,
    NoShapeRulesError,
    classify_face_shape,
    get_frame_styles,
)

from .serializers import (
    FamilySerializer,
    FrameStyleSerializer,
    GarmentSerializer,
    MeasurementsSerializer,
    PairingSerializer,
    ShadeSerializer,
    ShapeSerializer,
)

CARD_NOT_FOUND = "We could not find this card ID."


class CardResolveThrottle(AnonRateThrottle):
    scope = "card_resolve"


class CardInputSerializer(serializers.Serializer):
    card = serializers.CharField(max_length=32)


class GarmentListView(APIView):
    def get(self, request):
        return Response(GarmentSerializer(list_garments(), many=True).data)


class FamilyListView(APIView):
    def get(self, request):
        return Response(FamilySerializer(list_families(), many=True).data)


class CardResolveView(APIView):
    throttle_classes = [CardResolveThrottle]

    def post(self, request):
        form = CardInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        try:
            card = resolve_card(form.validated_data["card"])
        except InvalidCardError:
            return Response({"detail": CARD_NOT_FOUND}, status=404)
        return Response({"card": card.code, "tone": card.skin_tone.label})


class ShadeListView(APIView):
    throttle_classes = [CardResolveThrottle]

    def get(self, request):
        card_text = request.query_params.get("card", "")[:32]
        family_slug = request.query_params.get("family", "")
        if not card_text or not family_slug:
            return Response({"detail": "Both card and family are required."}, status=400)
        try:
            card = resolve_card(card_text)
        except InvalidCardError:
            return Response({"detail": CARD_NOT_FOUND}, status=404)
        family = get_family(family_slug)
        if family is None:
            return Response({"detail": "Color family not found."}, status=404)
        recommendations = get_visible_shades(card.skin_tone, family)
        return Response(ShadeSerializer(recommendations, many=True).data)


class PairingListView(APIView):
    def get(self, request):
        shade_text = request.query_params.get("shade", "")
        bottom_slug = request.query_params.get("bottom_type", "")
        if not shade_text or not bottom_slug:
            return Response(
                {"detail": "Both shade and bottom_type are required."}, status=400
            )
        if not shade_text.isdigit():
            return Response({"detail": "shade must be a number."}, status=400)
        shade = get_shade(int(shade_text))
        bottom = get_bottom_type(bottom_slug)
        if shade is None or bottom is None:
            return Response({"detail": "Shade or bottom type not found."}, status=404)
        return Response(PairingSerializer(get_pairings(shade, bottom), many=True).data)

class SunglassesThrottle(AnonRateThrottle):
    scope = "sunglasses_classify"


class SunglassesClassifyView(APIView):
    """Four numbers in, face shape and frame styles out. Nothing is saved."""

    throttle_classes = [SunglassesThrottle]

    def post(self, request):
        if not getattr(settings, "SUNGLASSES_ENABLED", False):
            raise Http404
        form = MeasurementsSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        try:
            result = classify_face_shape(**form.validated_data)
        except InvalidMeasurementError:
            return Response(
                {"detail": "These measurements do not look like a face. Try another photo."},
                status=400,
            )
        except NoShapeRulesError:
            return Response({"detail": "Face shapes are not set up yet."}, status=503)
        alternative = (
            ShapeSerializer(result.alternative).data if result.alternative else None
        )
        return Response(
            {
                "shape": ShapeSerializer(result.primary).data,
                "alternative": alternative,
                "frames": FrameStyleSerializer(
                    get_frame_styles(result.primary), many=True
                ).data,
            }
        )
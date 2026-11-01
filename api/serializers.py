from rest_framework import serializers

from catalog.models import BottomType, ColorFamily, GarmentType
from catalog.services import customer_label, get_bottom_types
from sunglasses.models import FaceShapeRule, FrameStyle


class BottomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomType
        fields = ["name", "slug"]


class GarmentSerializer(serializers.ModelSerializer):
    bottom_types = serializers.SerializerMethodField()

    class Meta:
        model = GarmentType
        fields = ["name", "slug", "has_pairing", "bottom_types"]

    def get_bottom_types(self, garment):
        # Same service the pages use, so Women's Kurta gets an empty list.
        return BottomTypeSerializer(get_bottom_types(garment), many=True).data


class FamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = ColorFamily
        fields = ["name", "slug", "sort_order"]


class ShadeSerializer(serializers.Serializer):
    """One styling suggestion. Input is a ShadeRecommendation row."""

    id = serializers.IntegerField(source="shade_id", read_only=True)
    name = serializers.CharField(source="shade.name", read_only=True)
    hex = serializers.CharField(source="shade.hex", read_only=True)
    label = serializers.SerializerMethodField()

    def get_label(self, recommendation):
        return customer_label(recommendation.status)


class PairingSerializer(serializers.Serializer):
    """One bottom-wear color suggestion. Input is an OutfitPairing row."""

    bottom_color_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="bottom_color.name", read_only=True)
    hex = serializers.CharField(source="bottom_color.hex", read_only=True)
    rank = serializers.IntegerField(read_only=True)

class MeasurementsSerializer(serializers.Serializer):
    """The four numbers from the browser. Nothing else is accepted."""

    face_length = serializers.FloatField()
    forehead_width = serializers.FloatField()
    cheekbone_width = serializers.FloatField()
    jaw_width = serializers.FloatField()

    def to_internal_value(self, data):
        if isinstance(data, dict):
            extra = set(data) - set(self.fields)
            if extra:
                raise serializers.ValidationError(
                    {"detail": "Only the four measurements are accepted."}
                )
        return super().to_internal_value(data)


class ShapeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceShapeRule
        fields = ["name", "slug"]


class FrameStyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameStyle
        fields = ["name", "slug", "note", "rank", "image_file"]
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from api.models import Route, Trailhead, Node


class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class NodeListSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return [{"lat": lat, "lon": lon} for (lat, lon) in instance]


class RouteSerializer(serializers.ModelSerializer):
    nodes = NodeListSerializer()

    class Meta:
        model = Route
        fields = (
            "id",
            "length_km",
            "trailhead",
            "trail_network",
            "elevation_gain",
            "elevation_loss",
            "is_loop",
            "nodes",
            "quality",
        )

    def to_representation(self, instance):
        base = super().to_representation(instance)
        return {
            'travel_time': int(self.context['trailheads'][instance.trailhead] / 60),
            **base,
        }



class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ("osm_id", "lat", "lon")


class TrailheadSerializer(serializers.ModelSerializer):
    node = NodeSerializer()

    class Meta:
        model = Trailhead
        fields = ("name", "id", "node")

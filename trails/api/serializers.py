from rest_framework import serializers

from api.models import Route


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ('length_km', 'trailhead', 'trail_network', 'elevation_gain', 'elevation_loss', 'is_loop')


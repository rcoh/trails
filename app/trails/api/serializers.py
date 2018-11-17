import copy
from enum import Enum

import geopy.distance
from measurement.measures import Distance
from rest_framework import serializers
from rest_framework.fields import empty, _UnvalidatedField

from api.models import Route, Trailhead, Node


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ("osm_id", "lat", "lon")


class TrailheadSerializer(serializers.ModelSerializer):
    node = NodeSerializer()

    class Meta:
        model = Trailhead
        fields = ("name", "id", "node")


class Measurement(Enum):
    Distance = 0
    Height = 1

    def build(self, unit_system: "UnitSystem", value: float):
        if self == Measurement.Distance:
            if unit_system == UnitSystem.Metric:
                return Distance(km=value)
            elif unit_system == UnitSystem.Imperial:
                return Distance(mi=value)
        elif self == Measurement.Height:
            if unit_system == UnitSystem.Metric:
                return Distance(m=value)
            elif unit_system == UnitSystem.Imperial:
                return Distance(ft=value)
        raise Exception()


class UnitSystem(Enum):
    Metric = "metric"
    Imperial = "imperial"


def united(obj, unit, precision):
    return round(getattr(obj, unit), precision)


class HeightSerializer(serializers.Serializer):
    def to_representation(self, instance):
        if self.context["unit"] == UnitSystem.Metric:
            return united(instance, "m", 0)
        elif self.context["unit"] == UnitSystem.Imperial:
            return united(instance, "ft", 0)
        else:
            raise Exception()


class DistanceSerializer(serializers.Serializer):
    def to_representation(self, instance):
        if self.context["unit"] == UnitSystem.Metric:
            return united(instance, "km", self.context.get('precision', 1))
        elif self.context["unit"] == UnitSystem.Imperial:
            return united(instance, "mi", self.context.get('precision', 1))
        else:
            raise Exception()


class NodeListSerializer(serializers.Serializer):
    def to_representation(self, instance):
        h_ser = HeightSerializer(context=self.context)
        d_ser = DistanceSerializer(context={**self.context, 'precision': 10})
        dist = Distance(m=0)
        res = []
        prev = None
        for (lat, lon, elevation) in instance:
            if prev is not None:
                dist += Distance(m=geopy.distance.great_circle(prev, (lat, lon)).m)

            prev = (lat, lon)

            res.append({
                "lat": lat,
                "lon": lon,
                "elevation": h_ser.to_representation(Distance(m=elevation)),
                "distance": d_ser.to_representation(dist)
            })
        return res


class RangeField(serializers.Serializer):
    min = _UnvalidatedField()
    max = _UnvalidatedField()

    def __init__(self, instance=None, data=empty, **kwargs):
        child = kwargs.pop("child")
        self.min = copy.deepcopy(child)
        self.max = copy.deepcopy(child)
        super().__init__(instance, data, **kwargs)
        self.min.bind(field_name="min", parent=self)
        self.max.bind(field_name="max", parent=self)

    def to_representation(self, instance):
        return {
            "min": self.min.to_representation(instance["min"]),
            "max": self.max.to_representation(instance["max"]),
        }


class HistogramSerializer(serializers.Serializer):
    num_routes = serializers.IntegerField()
    num_trailheads = serializers.IntegerField()
    elevation = RangeField(child=HeightSerializer())
    distance = RangeField(child=DistanceSerializer())
    travel_time = RangeField(child=serializers.IntegerField())
    trailheads = TrailheadSerializer(many=True)


class RouteSerializer(serializers.ModelSerializer):
    nodes = NodeListSerializer()
    trailhead = TrailheadSerializer()
    length = DistanceSerializer()
    elevation_gain = HeightSerializer()
    elevation_loss = HeightSerializer()

    class Meta:
        model = Route
        fields = (
            "id",
            "length",
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
            "travel_time": int(self.context["trailheads"][instance.trailhead] / 60),
            **base,
        }

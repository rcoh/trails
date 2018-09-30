from collections import defaultdict
from typing import Optional, NamedTuple, Dict

from django.contrib.gis.geos import Point
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.models import Trailhead, Route
from api.serializers import TrailheadSerializer, RouteSerializer
from api.traveltime import get_travel_times_cached


class TrailheadFilter(NamedTuple):
    location: Point
    max_travel_time_minutes: float = 25
    travel_mode: str = "driving"
    distance_km_filter: float = 50


class Tolerance(NamedTuple):
    value: float
    tolerance: float

    def bounds(self):
        return self.value - self.tolerance, self.value + self.tolerance


Length = "length"
Elevation = "elevation"
Travel = "travel"


class Ordering(NamedTuple):
    field: str
    asc: bool

    def apply(self, queryset, trailhead_travel_map: Dict[Trailhead, int]):
        prefix = "" if self.asc else "-"
        if self.field == Length:
            return queryset.order_by(prefix + "length_km")
        elif self.field == Elevation:
            return queryset.order_by(prefix + "elevation_gain")
        elif self.field == Travel:
            return sorted(
                queryset, key=lambda route: trailhead_travel_map[route.trailhead]
            )


class GeneralFilter(NamedTuple):
    trailhead_filter: TrailheadFilter
    length_filter: Tolerance
    elevation_filter: Optional[Tolerance]
    ordering: Optional[Ordering]


class NearbyTrailheadRequest(serializers.Serializer):
    lat = serializers.FloatField(required=True)
    lon = serializers.FloatField(required=True)
    max_travel_time_minutes = serializers.IntegerField(required=False, default=25)
    travel_mode = serializers.ChoiceField(
        ["driving"], required=False, default="driving"
    )

    def to_nt(self, validated_data):
        return TrailheadFilter(
            location=Point(validated_data["lat"], validated_data["lon"]),
            max_travel_time_minutes=validated_data["max_travel_time_minutes"],
            travel_mode=validated_data["travel_mode"],
        )


class ToleranceFilter(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        if "default_tolerance" in kwargs:
            self.default_tolerance = kwargs.pop("default_tolerance")

        super().__init__(*args, **kwargs)

    value = serializers.FloatField()
    tolerance = serializers.FloatField()

    def to_nt(self, validated_data):
        return Tolerance(validated_data["value"], validated_data["tolerance"])


class OrderingSerializer(serializers.Serializer):
    field = serializers.ChoiceField([Length, Travel, Elevation])
    asc = serializers.BooleanField()

    def to_nt(self, validated_data):
        return Ordering(validated_data["field"], validated_data["asc"])


class GeneralRequest(serializers.Serializer):
    location_filter = NearbyTrailheadRequest()
    length = ToleranceFilter(default_tolerance=1)
    ordering = OrderingSerializer(required=False)

    def to_nt(self, validated_data):
        if validated_data.get("ordering"):
            ordering = self.fields["ordering"].to_nt(validated_data["ordering"])
        else:
            ordering = None
        return GeneralFilter(
            trailhead_filter=self.fields["location_filter"].to_nt(
                validated_data["location_filter"]
            ),
            elevation_filter=None,
            length_filter=self.fields["length"].to_nt(validated_data["length"]),
            ordering=ordering,
        )


def trailheads_near(filter: TrailheadFilter) -> Dict[Trailhead, int]:
    possible_trailheads = Trailhead.trailheads_near(
        filter.location, max_distance_km=filter.distance_km_filter
    )
    return get_travel_times_cached(filter.location, possible_trailheads)


# Create your views here.
@api_view(["POST"])
def nearby_trailheads(request):
    request = NearbyTrailheadRequest(data=request.data)
    if not request.is_valid():
        return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)
    general = request.to_nt(request.validated_data)
    time_filtered = trailheads_near(general)
    resp = []
    for trailhead, time in time_filtered.items():
        resp.append(
            dict(
                trailhead=TrailheadSerializer(trailhead).data, travel_time_seconds=time
            )
        )
    resp.sort(key=lambda kv: kv["travel_time_seconds"])
    return Response(resp, status=200)


def find_loops(filter: GeneralFilter):
    possible_trailheads = trailheads_near(filter.trailhead_filter)
    min_length, max_length = filter.length_filter.bounds()
    filtered = Route.objects.filter(
        trailhead__in=possible_trailheads,
        length_km__lt=max_length,
        length_km__gt=min_length,
    )

    if filtered.count() == 0:
        closest_matches = (
            Route.objects.filter(trailhead__in=possible_trailheads)
            .extra(select={"delta_len": f"abs(length_km-{filter.length_filter.value})"})
            .order_by("delta_len")[:5]
        )
        filtered = Route.objects.filter(id__in=closest_matches)
    if filter.ordering is not None:
        filtered = filter.ordering.apply(filtered, possible_trailheads)
    return filtered


@api_view(["POST"])
def histogram(request):
    request = GeneralRequest(data=request.data)
    if not request.is_valid():
        return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)

    filter = request.to_nt(request.validated_data)
    routes = find_loops(filter)
    # cached
    possible_trailheads = trailheads_near(filter.trailhead_filter)

    ret = {
        "num_routes": len(routes),
        "num_trailheads": len(possible_trailheads),
        "elevation": {
            "max": max([route.elevation_gain for route in routes]),
            "min": min([route.elevation_gain for route in routes]),
        },
        "travel_time": {
            "max": max(possible_trailheads.values()),
            "min": min(possible_trailheads.values()),
        },
        "distance": {
            "max": max(route.length_km for route in routes),
            "min": min(route.length_km for route in routes),
        },
    }
    return Response(ret, status=200)


@api_view(["POST"])
def top_trails(request):
    request = GeneralRequest(data=request.data)
    if not request.is_valid():
        return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)
    filter = request.to_nt(request.validated_data)
    routes = find_loops(filter)[:5]
    return Response(RouteSerializer(routes, many=True).data, status=200)

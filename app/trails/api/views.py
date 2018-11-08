from typing import Optional, NamedTuple, Dict

from django.contrib.gis.geos import Point
from django.db.models import Max, Min, Sum
from django.http import HttpResponse
from measurement.measures import Distance
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.models import Trailhead, Route, TrailNetwork
from api.serializers import (
    TrailheadSerializer,
    RouteSerializer,
    UnitSystem,
    HistogramSerializer,
    Measurement,
)
from api.traveltime import get_travel_times_cached


class TrailheadFilter(NamedTuple):
    location: Point
    max_travel_time_minutes: float = 25
    travel_mode: str = "driving"
    distance_km_filter: float = max_travel_time_minutes


class Tolerance(NamedTuple):
    value: Distance
    tolerance_pct: float

    def bounds(self):
        return (
            self.value - self.value * self.tolerance_pct,
            self.value + self.value * self.tolerance_pct,
        )


Length = "length"
Elevation = "elevation"
Travel = "travel"


class Ordering(NamedTuple):
    field: str
    asc: bool

    def apply(self, queryset, trailhead_travel_map: Dict[Trailhead, int]):
        reverse = "" if self.asc else "-"
        if self.field == Length:
            return queryset.order_by(reverse + "length")
        elif self.field == Elevation:
            return queryset.order_by(reverse + "elevation_gain")
        elif self.field == Travel:
            return sorted(
                queryset, key=lambda route: trailhead_travel_map[route.trailhead]
            )


class GeneralFilter(NamedTuple):
    units: UnitSystem
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
        self.measurement = kwargs.pop("measurement")
        super().__init__(*args, **kwargs)

    value = serializers.FloatField()
    tolerance = serializers.FloatField()

    def to_nt(self, validated_data, units):
        return Tolerance(
            self.measurement.build(units, validated_data["value"]),
            validated_data["tolerance"],
        )


class OrderingSerializer(serializers.Serializer):
    field = serializers.ChoiceField([Length, Travel, Elevation])
    asc = serializers.BooleanField()

    def to_nt(self, validated_data):
        return Ordering(validated_data["field"], validated_data["asc"])


class GeneralRequest(serializers.Serializer):
    units = serializers.ChoiceField(["metric", "imperial"])
    location_filter = NearbyTrailheadRequest()
    length = ToleranceFilter(measurement=Measurement.Distance)
    elevation = ToleranceFilter(measurement=Measurement.Height, required=False)
    ordering = OrderingSerializer(required=False)

    def to_nt(self, validated_data):
        if validated_data.get("ordering"):
            ordering = self.fields["ordering"].to_nt(validated_data["ordering"])
        else:
            ordering = None

        if validated_data["units"] == "metric":
            units = UnitSystem.Metric
        else:
            units = UnitSystem.Imperial
        return GeneralFilter(
            trailhead_filter=self.fields["location_filter"].to_nt(
                validated_data["location_filter"]
            ),
            elevation_filter=None,
            length_filter=self.fields["length"].to_nt(validated_data["length"], units),
            ordering=ordering,
            units=units,
        )


def trailheads_near(
        filter: TrailheadFilter, length: Optional[Tolerance]
) -> Dict[Trailhead, int]:
    possible_trailheads = Trailhead.trailheads_near(
        filter.location, max_distance_km=filter.distance_km_filter
    )

    if length:
        possible_trailheads = possible_trailheads.filter(
            trail_network__trail_length__gt=length.value
        )
    return get_travel_times_cached(filter.location, possible_trailheads)


@api_view(["POST"])
def nearby_trailheads(request):
    request = NearbyTrailheadRequest(data=request.data)
    if not request.is_valid():
        return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)
    general: TrailheadFilter = request.to_nt(request.validated_data)
    time_filtered = trailheads_near(general, None)
    resp = []
    for trailhead, time in time_filtered.items():
        resp.append(
            dict(
                trailhead=TrailheadSerializer(trailhead).data, travel_time_seconds=time
            )
        )
    resp.sort(key=lambda kv: kv["travel_time_seconds"])
    return Response(resp, status=200)


def find_loops(loop_filter: GeneralFilter):
    possible_trailheads: Dict[Trailhead, int] = trailheads_near(
        loop_filter.trailhead_filter, loop_filter.length_filter
    )
    print(f"found {len(possible_trailheads)} potential trailheads")
    min_length, max_length = loop_filter.length_filter.bounds()
    filtered = Route.objects.defer("nodes").filter(
        trailhead__in=possible_trailheads, length__lt=max_length, length__gt=min_length
    )

    if filtered.count() < 5:
        closest_matches = (
            Route.objects.filter(trailhead__in=possible_trailheads)
                .extra(select={"delta_len": f"abs(length-{loop_filter.length_filter.value.m})"})
                .order_by("delta_len")[:5]
        )
        filtered = Route.objects.filter(id__in=closest_matches)
    if loop_filter.ordering is not None:
        filtered = loop_filter.ordering.apply(filtered, possible_trailheads)
    return filtered, possible_trailheads


@api_view(["POST"])
def histogram(request):
    request = GeneralRequest(data=request.data)
    if not request.is_valid():
        return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)

    filter = request.to_nt(request.validated_data)
    routes, possible_trailheads = find_loops(filter)

    if routes.count() > 0:
        actual_trailheads = {
            route.trailhead: possible_trailheads[route.trailhead] for route in routes
        }
        results = routes.aggregate(Max('elevation_gain'), Min('elevation_gain'), Max('length'), Min('length'))
        ret = {
            "num_routes": len(routes),
            "num_trailheads": len(actual_trailheads),
            "elevation": {
                "max": results['elevation_gain__max'],
                "min": results['elevation_gain__min'],
            },
            "travel_time": {
                "max": max(actual_trailheads.values()),
                "min": min(actual_trailheads.values()),
            },
            "distance": {
                "max": results['length__max'],
                "min": results['length__min'],
            },
        }
        ret = HistogramSerializer(ret, context=dict(unit=filter.units)).data
    else:
        ret = {"num_routes": 0}
    return Response(
        {
            **ret,
            "units": filter.units.value
        }, status=200
    )


@api_view(["GET"])
def export_gpx(request):
    id = request.query_params["id"]
    route = Route.objects.get(id=id)
    response = HttpResponse(route.to_gpx(), content_type="application/gpx")
    response["Content-Disposition"] = "attachment; filename=route.gpx"
    return response


@api_view(["POST"])
def top_trails(request):
    request = GeneralRequest(data=request.data)
    if not request.is_valid():
        return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)
    filter = request.to_nt(request.validated_data)
    routes, trailheads = find_loops(filter)
    resp_data = {
        "routes": RouteSerializer(
            routes[:10],
            many=True,
            context=dict(trailheads=trailheads, unit=filter.units),
        ).data,
        "units": filter.units.value,
    }
    return Response(resp_data, status=200)


@api_view(["GET"])
def statusz(request):
    return Response({}, status=200)

@api_view(["GET"])
def meta(request):
    num_networks = TrailNetwork.objects.count()
    network_size = TrailNetwork.objects.aggregate(Sum('trail_length'))['trail_length__sum']
    num_routes = Route.objects.count()
    num_trailheads = Trailhead.objects.count()
    route_length = Route.objects.aggregate(Sum('length'))['length__sum']

    return Response(dict(
        num_networks=num_networks,
        total_distance=network_size.mi,
        num_routes=num_routes,
        num_trailheads=num_trailheads,
        route_length=route_length.mi
    ))

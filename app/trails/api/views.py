from typing import Optional, NamedTuple, Dict, Any

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
            # we're going to have to download everything (no limit, so make sure we don't select nodes)
            queryset = queryset.defer("nodes")
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
            location=Point(validated_data["lon"], validated_data["lat"]),
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

    def or_none(self, field: str, validated_data: Dict[str, Any], **extra):
        if validated_data.get(field):
            return self.fields[field].to_nt(validated_data[field], **extra)
        else:
            return None

    def to_nt(self, validated_data):
        ordering = self.or_none("ordering", validated_data)
        if validated_data["units"] == "metric":
            units = UnitSystem.Metric
        else:
            units = UnitSystem.Imperial
        length_filter = self.or_none("length_filter", validated_data)
        elevation_filter = self.or_none("elevation_filter", validated_data, units=units)


        return GeneralFilter(
            trailhead_filter=self.fields["location_filter"].to_nt(
                validated_data["location_filter"]
            ),
            elevation_filter=elevation_filter,
            length_filter=self.fields["length"].to_nt(validated_data["length"], units),
            ordering=ordering,
            units=units,
        )


def trailheads_near(trailhead_filter: TrailheadFilter) -> Dict[Trailhead, int]:
    possible_trailheads = Trailhead.trailheads_near(
        trailhead_filter.location, max_distance_km=trailhead_filter.distance_km_filter
    )

    return get_travel_times_cached(trailhead_filter.location, possible_trailheads)


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
        loop_filter.trailhead_filter
    )
    print(f"found {len(possible_trailheads)} potential trailheads")
    min_length, max_length = loop_filter.length_filter.bounds()
    filtered = (
        Route.objects.defer("osm_rep")
            .filter(
            trailhead__in=possible_trailheads,
            length__lt=max_length,
            length__gt=min_length,
        )
            .select_related("trailhead__node")
    )

    if filtered.count() < 5:
        closest_matches = (
            Route.objects.filter(trailhead__in=possible_trailheads)
                .extra(
                select={"delta_len": f"abs(length-{loop_filter.length_filter.value.m})"}
            )
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
    routes = routes.defer("nodes")
    num_routes = routes.count()

    if num_routes > 0:
        actual_trailheads = {
            route.trailhead: possible_trailheads[route.trailhead]
            for route in routes.only("trailhead")
        }
        routes = routes.filter(trailhead__in=actual_trailheads)
        results = routes.aggregate(
            Max("elevation_gain"), Min("elevation_gain"), Max("length"), Min("length")
        )
        ret = {
            "num_routes": num_routes,
            "num_trailheads": len(actual_trailheads),
            "elevation": {
                "max": results["elevation_gain__max"],
                "min": results["elevation_gain__min"],
            },
            "travel_time": {
                "max": max(actual_trailheads.values()),
                "min": min(actual_trailheads.values()),
            },
            "distance": {"max": results["length__max"], "min": results["length__min"]},
            "trailheads": actual_trailheads,
        }
        ret = HistogramSerializer(ret, context=dict(unit=filter.units)).data
    else:
        ret = {"num_routes": 0}
    return Response({**ret, "units": filter.units.value}, status=200)


@api_view(["GET"])
def export_gpx(request):
    id = request.query_params["id"]
    route = Route.objects.get(id=id)
    download_name = route.name.replace(" ", "-").lower()
    if download_name == "":
        download_name = "route"
    response = HttpResponse(route.export_gpx(), content_type="application/gpx")
    response["Content-Disposition"] = f"attachment; filename={download_name}.gpx"
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
    network_size = TrailNetwork.objects.aggregate(Sum("trail_length"))[
        "trail_length__sum"
    ]
    num_routes = Route.objects.count()
    num_trailheads = Trailhead.objects.count()
    route_length = Route.objects.aggregate(Sum("length"))["length__sum"]

    return Response(
        dict(
            num_networks=num_networks,
            total_distance=network_size.mi,
            num_routes=num_routes,
            num_trailheads=num_trailheads,
            route_length=route_length.mi,
        )
    )

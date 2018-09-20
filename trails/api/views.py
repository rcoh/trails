from django.contrib.gis.geos import Point
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.models import Trailhead
from api.serializers import TrailheadSerializer
from api.traveltime import get_travel_times_cached


class NearbyTrailheadRequest(serializers.Serializer):
    lat = serializers.FloatField(required=True)
    lon = serializers.FloatField(required=True)
    max_travel_time_minutes = serializers.IntegerField(required=False, default=25)
    travel_mode = serializers.ChoiceField(
        ["driving"], required=False, default="driving"
    )


# Create your views here.
@api_view(["POST"])
def nearby_trailheads(request):
    """
    List all code snippets, or create a new snippet.
    """
    request = NearbyTrailheadRequest(data=request.data)
    if not request.is_valid():
       return Response(request.errors, status=status.HTTP_400_BAD_REQUEST)

    request = request.data
    point = Point(request['lat'], request['lon'])
    possible_trailheads = Trailhead.trailheads_near(point, max_distance_km=50)
    time_filtered = get_travel_times_cached(point, possible_trailheads)
    resp = []
    for trailhead, time in time_filtered.items():
        resp.append(dict(trailhead=TrailheadSerializer(trailhead).data, travel_time_seconds=time))
    resp.sort(key=lambda kv: kv['travel_time_seconds'])
    return Response(resp, status=200)



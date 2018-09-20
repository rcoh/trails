from django.shortcuts import render
from rest_framework import status, serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from googlemaps import geocoding, client


class NearbyTrailheadRequest(serializers.Serializer):
    address = serializers.CharField(required=True)
    max_travel_time_minutes = serializers.IntegerField(required=False, default=25)
    travel_mode = serializers.ChoiceField(['car', 'bike','walk', 'transit'], required=False, default='car')



# Create your views here.
@api_view(['POST'])
def nearby_trailheads(request):
    """
    List all code snippets, or create a new snippet.
    """
    request = NearbyTrailheadRequest(data=request.data)
    # if request.is_valid():
    #     geocode =



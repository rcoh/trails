import json

from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

from est.models import TrailNetwork


def default_map(request):
    # TODO: move this token to Django settings from an environment variable
    # found in the Mapbox account settings and getting started instructions
    # see https://www.mapbox.com/account/ under the "Access tokens" section
    mapbox_access_token = 'pk.eyJ1IjoiZXZlcnlzaW5nbGV0cmFpbCIsImEiOiJja2JsNmV2YjcwaWY5MnFxbmdtanF4aGUyIn0.ioFGm3P5s1kOpv7fJerp7g'
    network = TrailNetwork.objects.order_by('-total_length').first()
    return render(request, 'default.html',
                  {
                      'mapbox_access_token': mapbox_access_token,
                      'perimeter': network.trails.json,
                      'center': json.dumps([network.bounding_box.centroid.x, network.bounding_box.centroid.y])
                  })

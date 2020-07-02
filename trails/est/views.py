import json

import attr
import cattr
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.urls import reverse

from est.models import TrailNetwork, Import, Circuit
from est.postman import circuits


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
                      'center': json.dumps([network.poly.centroid.x, network.poly.centroid.y])
                  })


def about(request):
    return render(request, "about.html")


@attr.s(auto_attribs=True, frozen=True)
class LatLng:
    lng: float
    lat: float


@attr.s(auto_attribs=True, frozen=True)
class AreasRequest:
    sw: LatLng
    ne: LatLng

    def to_poly(self):
        return Polygon.from_bbox(
            (*attr.astuple(self.sw), *attr.astuple(self.ne))
        )


COLORS = ["5bc0eb", "fde74c", "9bc53d", "c3423f", "404e4d"]


def humanize(n: float):
    n = int(n * 10) / 10
    if abs(round(n) - n) < 0.01:
        n = int(n)
    return n


def circuit_description(network: TrailNetwork):
    circuit = Circuit.objects.filter(network=network).first()
    if circuit is not None:
        return f"Full tour: " \
               f"{humanize(circuit.total_length.mi)} miles. " \
               f"<a href=\"{reverse(gpx, kwargs=dict(circuit_id=circuit.id))}\">Download GPX</a>"
    else:
        return f'<a id="{network.id}" href="#">Compute complete tour</a>'


def circuit_status(network: TrailNetwork):
    circuit = Circuit.objects.filter(network=network).first()
    if circuit is not None:
        return "complete"
    else:
        return "undone"


def areas(request):
    data: AreasRequest = cattr.structure(json.loads(request.body), AreasRequest)
    bounds = data.to_poly()
    networks = TrailNetwork.active().filter(poly__intersects=bounds)
    geojson = dict(
        type='FeatureCollection',
        features=[
            dict(
                id=i,
                type='Feature',
                properties=dict(
                    circuit_status=circuit_status(network),
                    id=network.id,
                    description=f"""
    <h4>{network.name}</h4>
    <div class="map-popover">
        <div class="milage">{humanize(network.total_length.mi)} miles of trails</div>
        <div class="tour">{circuit_description(network)}</div>
        <div class="zoom"><a href="#" id="{network.id}-zoom">Zoom</a></div>
    </div>
    """,
                    fill_color='#' + COLORS[i % len(COLORS)],
                    center=[network.poly.centroid.x, network.poly.centroid.y],
                    bb=[network.poly.extent[0:2], network.poly.extent[2:4]],
                ), geometry=json.loads(network.poly.json)
            )
            for i, network in enumerate(networks)
        ]
    )

    return JsonResponse(dict(ok=True, data=geojson))


def gpx(request, circuit_id: str) -> HttpResponse:
    circuit = Circuit.objects.get(id=circuit_id)
    response = HttpResponse(circuit.to_gpx(), content_type="application/gpx")
    response["Content-Disposition"] = f"attachment; filename={circuit.network.name}.gpx"
    return response


def circuit(request, network_id: str) -> JsonResponse:
    return JsonResponse(dict(ok=True, data=circuits(TrailNetwork.objects.get(id=network_id)).total_length.mi))


def base_map(request):
    active_imports = Import.objects.filter(active=True)
    polys = [i.border for i in active_imports]
    centroid = MultiPolygon(polys).centroid
    coords = [42.389268, -71.088265]
    coords.reverse()
    return JsonResponse({
        "center": coords
    })

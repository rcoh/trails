import json
from typing import Any, Dict, List

import attr
import cattr
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.serializers import deserialize, serialize
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from est.models import TrailNetwork, Import, Circuit, Complete, InProgress, Error
from est.postman import find_or_compute_circuit


@ensure_csrf_cookie
def default_map(request):
    # TODO: move this token to Django settings from an environment variable
    # found in the Mapbox account settings and getting started instructions
    # see https://www.mapbox.com/account/ under the "Access tokens" section
    return render(request, 'default.html')


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


@attr.s(auto_attribs=True, frozen=True)
class ExternalImport:
    import_record: str
    networks: str


def external_import(request):
    data: ExternalImport = cattr.structure(json.loads(request.body), ExternalImport)
    import_record = deserialize('json', data.import_record)
    networks = deserialize('json', data.networks)
    for rec in import_record:
        overlaps = Import.objects.filter(border__intersects=rec.object.border, active=True)
        if overlaps.exists():
            if rec.object.id == overlaps.first().id:
                return JsonResponse(status=400, data=dict(status="already done"))
            return JsonResponse(status=400, data=dict(status="no import", msg="region overlap",
                                                      rec=json.loads(serialize('json', overlaps))))
        rec.save()
    for network in networks:
        network.save()
    return JsonResponse(data=dict(status="ok"))


COLORS = ["5bc0eb", "fde74c", "9bc53d", "c3423f", "404e4d"]


def humanize(n: float):
    n = int(n * 10) / 10
    if abs(round(n) - n) < 0.01:
        n = int(n)
    return n


def circuit_description(network: TrailNetwork):
    circuit = Circuit.objects.filter(network=network).first()
    recompute_html = f'<a id="{network.id}" href="#">Compute complete tour</a>'
    if circuit is not None:
        if circuit.status == Complete:
            return f"Full tour: " \
                   f"{humanize(circuit.total_length.mi)} miles. " \
                   f"<a href=\"{reverse(gpx, kwargs=dict(circuit_id=circuit.id))}\">Download GPX</a>"
        elif circuit.status == InProgress:
            return f"Circuit computation in progress (started {naturaltime(circuit.created_at)})"
        elif circuit.status == Error:
            return f"Circuit failed to be built. {circuit.error}. Recompute: {recompute_html}"
    else:
        return recompute_html


def circuit_status(network: TrailNetwork):
    circuit = Circuit.objects.filter(network=network).first()
    if circuit is not None:
        return "complete"
    else:
        return "undone"


def html_description(network: TrailNetwork) -> str:
    return f"""
        <h4>{network.name}</h4>
        <div class="map-popover">
            <div class="milage">{humanize(network.total_length.mi)} miles of trails</div>
            <div class="tour">{circuit_description(network)}</div>
            <div class="zoom"><a href="#" id="{network.id}-zoom">Zoom</a></div>
        </div>
        """


def network(request, network_id):
    network = TrailNetwork.objects.get(id=network_id)
    return JsonResponse(data=dict(
        html=html_description(network=network)
    ))


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
                    description=html_description(network),
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


def compute_circuit(request, network_id: str) -> JsonResponse:
    trail_network = TrailNetwork.objects.get(id=network_id)
    circuit_in_progress = find_or_compute_circuit(trail_network)
    return JsonResponse(
        dict(ok=True, data=dict(circuit_id=circuit_in_progress.id), html=html_description(trail_network)))


def base_map(request):
    active_imports = Import.objects.filter(active=True)
    polys = [i.border for i in active_imports]
    centroid = MultiPolygon(polys).centroid
    coords = [42.389268, -71.088265]
    coords.reverse()
    return JsonResponse({
        "center": coords
    })

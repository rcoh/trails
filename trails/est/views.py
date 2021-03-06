import json
from io import BytesIO
from json import JSONDecodeError
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
from measurement.measures import Distance
from networkx import read_gpickle

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


def import_ids(request, import_id):
    import_obj = Import.objects.prefetch_related('networks').filter(id=import_id).first()
    if import_obj is None:
        return JsonResponse(data=dict(ids=[], msg="Import not loaded yet"))
    else:
        return JsonResponse(data=dict(ids=[network.id for network in import_obj.networks.all()]))


def external_import(request):
    data: ExternalImport = cattr.structure(json.loads(request.body), ExternalImport)
    import_record = deserialize('json', data.import_record)
    networks = deserialize('json', data.networks)
    for rec in import_record:
        rec.object.active = False
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


def circuit_dict(circuit):
    ret = dict(
        id=circuit.id,
        since=naturaltime(circuit.created_at),
        status=circuit.get_status_display(),
        error=circuit.error
    )
    if circuit.status == Complete:
        ret['total_length'] = humanize(circuit.total_length.mi)
        ret['download_url'] = reverse('gpx', kwargs=dict(circuit_id=circuit.id))
    return ret


LENGTH_CACHE = {}


def get_network(request, network_id: str):
    try:
        network = TrailNetwork.objects.get(id=network_id)
    except TrailNetwork.DoesNotExist:
        return JsonResponse(status=404, data=dict(msg=f"Network {network_id} does not exist"))
    existing_circuit = Circuit.objects.filter(network=network).first()
    circuit = None
    if existing_circuit:
        circuit = circuit_dict(existing_circuit)
    if network_id in LENGTH_CACHE:
        print('cache hit')
        calculated = LENGTH_CACHE[network_id]
    else:
        graph = read_gpickle(BytesIO(network.graph.tobytes()))
        calculated = sum([w.length() for _, _, w in graph.edges.data('trail')], Distance(m=0))
        LENGTH_CACHE[network_id] = calculated

    return JsonResponse(data=dict(
        id=network.id,
        name=network.name,
        milage=humanize(calculated.mi),
        circuit=circuit,
        trailheads=dict(
            type='FeatureCollection',
            features=[dict(
                id=i,
                type='Feature',
                geometry=json.loads(trailhead.json)
            ) for i, trailhead in enumerate(network.trailheads)]
        ),
    ))


MAX_AREAS = 1000000


def status(request):
    base_request = json.loads(
        '{"sw":{"lng":-71.15263801635665,"lat":42.29651906359558},"ne":{"lng":-71.0238919836417,"lat":42.481880093902106}}')
    areas_request = cattr.structure(base_request, AreasRequest)
    bounds = areas_request.to_poly()
    view_area = bounds.area
    minumum_park_size = view_area / 5000
    networks = TrailNetwork.active().filter(poly__bboverlaps=bounds, area__gt=minumum_park_size)
    return JsonResponse(data=dict(
        num_networks=networks.count(),
        names=[network.name for network in networks]
    ))


MAX_TO_RETURN = 300


def areas(request):
    try:
        data: AreasRequest = cattr.structure(json.loads(request.body), AreasRequest)
    except JSONDecodeError:
        return JsonResponse(status=400, data=dict(status=400, error="Invalid JSON"))
    bounds = data.to_poly()
    networks = TrailNetwork.active().filter(poly__bboverlaps=bounds).order_by('-area')[:MAX_TO_RETURN].only('id',
                                                                                                            'poly')
    geojson = dict(
        type='FeatureCollection',
        features=[
            dict(
                id=network.id.int % MAX_AREAS,
                type='Feature',
                properties=dict(
                    id=network.id,
                    fill_color='#' + COLORS[network.id.int % len(COLORS)],
                    bb=[network.poly.extent[0:2], network.poly.extent[2:4]],
                ), geometry=json.loads(network.poly.json)
            )
            for network in networks
        ]
    )

    return JsonResponse(dict(ok=True, data=geojson))


def circuit_json(request, circuit_id: str) -> HttpResponse:
    circuit = Circuit.objects.get(id=circuit_id)
    return JsonResponse(data=dict(json=json.loads(circuit.route.json)))


def gpx(request, circuit_id: str) -> HttpResponse:
    circuit = Circuit.objects.get(id=circuit_id)
    response = HttpResponse(circuit.to_gpx(), content_type="application/gpx")
    response["Content-Disposition"] = f"attachment; filename={circuit.network.name}.gpx"
    return response


def compute_circuit(request, network_id: str) -> JsonResponse:
    trail_network = TrailNetwork.objects.get(id=network_id)
    circuit_in_progress = find_or_compute_circuit(trail_network)
    return JsonResponse(dict(ok=True, data=dict(circuit_id=circuit_in_progress.id)))


def base_map(request):
    active_imports = Import.objects.filter(active=True)
    polys = [i.border for i in active_imports]
    centroid = MultiPolygon(polys).centroid
    coords = [42.389268, -71.088265]
    coords.reverse()
    return JsonResponse({
        "center": coords
    })

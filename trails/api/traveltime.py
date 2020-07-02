import datetime
import sys
from typing import List, Dict
import requests
from django.contrib.gis.geos import Point
from django.db.models import QuerySet

from api.models import Trailhead, TravelTime, TravelCache

URL = "https://api.traveltimeapp.com/v4/time-filter"
API_KEY = "826197ad401f526445650d96aaad63b0"
APP_ID = "92be8391"

UNREACHABLE = sys.maxsize


def get_travel_times_cached(
    start_point: Point,
    target_locations: List[Trailhead],
    max_minutes=40,
    force_no_cache=False,
) -> Dict[Trailhead, int]:
    cached_results = TravelCache.objects.filter(
        start_point__distance_lte=(start_point, 1000)
    )
    if isinstance(target_locations, QuerySet):
        target_locations = target_locations.select_related("node")
    if cached_results and not force_no_cache:
        points = TravelTime.objects.filter(start_point=cached_results[0]).all()
        points_map = {point.osm_id: point.travel_time_minutes for point in points}
        trailhead_map = {
            trailhead.node.osm_id: trailhead for trailhead in target_locations
        }
        missing_points = trailhead_map.keys() - points_map.keys()
        if missing_points:
            results_from_api = get_travel_times_cached(
                start_point,
                [trailhead_map[t] for t in missing_points],
                max_minutes,
                force_no_cache=True,
            )
        else:
            results_from_api = {}

        results = {
            trailhead: points_map.get(
                trailhead.node.osm_id, results_from_api.get(trailhead)
            )
            for trailhead in target_locations
            if trailhead in results_from_api or trailhead.node.osm_id in points_map
        }
        return {k: time for k, time in results.items() if time < max_minutes * 60}
    else:
        results = get_travel_times(start_point, target_locations, max_minutes)
        cache_row = TravelCache(start_point=start_point)
        cache_row.save()
        travel_time_objects = [
            TravelTime(
                travel_time_minutes=time,
                osm_id=trailhead.node.osm_id,
                start_point=cache_row,
            )
            for trailhead, time in results.items()
        ]
        TravelTime.objects.bulk_create(travel_time_objects)
        return {k: time for k, time in results.items() if time < max_minutes * 60}


def get_travel_times(
    start_point: Point, target_locations: List[Trailhead], max_minutes=40
) -> Dict[Trailhead, int]:
    max_locations = 2000
    locations = [dict(id="__start", coords=dict(lng=start_point.x, lat=start_point.y))]
    for trailhead in target_locations[:max_locations]:
        locations.append(
            dict(
                id=f"{trailhead.node.osm_id}",
                coords=dict(lat=trailhead.node.lat, lng=trailhead.node.lon),
            )
        )

    req = dict(
        locations=locations,
        departure_searches=[
            dict(
                id="main",
                departure_location_id="__start",
                arrival_location_ids=[l["id"] for l in locations[1:]],
                transportation=dict(type="driving"),
                departure_time=datetime.datetime.utcnow().isoformat(),
                travel_time=max_minutes * 60,
                properties=["travel_time"],
            )
        ],
    )

    resp = requests.post(
        URL, json=req, headers={"X-Application-Id": APP_ID, "X-Api-Key": API_KEY}
    )

    resp_json = resp.json()
    ret: Dict[Trailhead, int] = {}
    trailhead_map = {trailhead.node.osm_id: trailhead for trailhead in target_locations}
    if "error_code" in resp_json:
        # Unsupported region
        if resp_json["error_code"] == 16:
            for location in target_locations:
                ret[trailhead_map[location.node.osm_id]] = (
                    location.node.distance(start_point).km * 60
                )
    if "results" not in resp_json:
        print(f"Drive time computation error: {resp_json}")
        return ret
    for location in resp_json["results"][0]["locations"]:
        osm_id = int(location["id"])
        ret[trailhead_map[osm_id]] = location["properties"][0]["travel_time"]
    for location in resp_json["results"][0]["unreachable"]:
        print("unreachable", location, start_point)
        osm_id = int(location)
        ret[trailhead_map[osm_id]] = UNREACHABLE

    return ret

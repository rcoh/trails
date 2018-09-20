import datetime
from typing import List, Dict
import requests
import requests_cache
from django.contrib.gis.geos import Point

from api.models import Trailhead, TravelTime, TravelCache

URL = "https://api.traveltimeapp.com/v4/time-filter"
API_KEY = "826197ad401f526445650d96aaad63b0"
APP_ID = "92be8391"

def get_travel_times_cached(start_point: Point, target_locations: List[Trailhead], max_minutes=40) -> Dict[
    Trailhead, int]:
    cached_results = TravelCache.objects.filter(start_point__distance_lte=(start_point, 1000))
    if cached_results:
        points = TravelTime.objects.filter(start_point=cached_results[0])
        trailhead_map = {trailhead.node.osm_id: trailhead for trailhead in target_locations}
        return {trailhead_map[point.osm_id]: point.travel_time_minutes for point in points}
    else:
        results = get_travel_times(start_point, target_locations, max_minutes)
        cache_row = TravelCache(start_point=start_point)
        cache_row.save()
        travel_time_objects = [TravelTime(travel_time_minutes=time, osm_id=trailhead.node.osm_id, start_point=cache_row) for trailhead, time in results.items()]
        TravelTime.objects.bulk_create(travel_time_objects)
        return results

def get_travel_times(
        start_point: Point, target_locations: List[Trailhead], max_minutes=40
) -> Dict[Trailhead, int]:
    locations = [dict(id="__start", coords=dict(lat=start_point.x, lng=start_point.y))]
    for trailhead in target_locations:
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
    print(resp_json)
    trailhead_map = {trailhead.node.osm_id: trailhead for trailhead in target_locations}
    ret = {}
    for location in resp_json["results"][0]["locations"]:
        osm_id = int(location["id"])
        ret[trailhead_map[osm_id]] = location["properties"][0]["travel_time"]
    return ret

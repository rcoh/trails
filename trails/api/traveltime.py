import datetime
import json
from typing import List
import requests

from api.models import Trailhead, Point

URL = "https://api.traveltimeapp.com/v4/time-filter"
API_KEY = "826197ad401f526445650d96aaad63b0"
APP_ID = "92be8391"


def get_travel_times(
    start_loc: Point, target_locations: List[Trailhead], max_minutes=40
):
    locations = [dict(id="__start", coords=dict(lat=start_loc.lat, lng=start_loc.lng))]
    for trailhead in target_locations:
        locations.append(
            dict(
                id=f"{trailhead.node.osm_id}",
                coords=dict(lat=trailhead.node.lat, lng=trailhead.node.lng),
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
    resp_json = requests.post(
        URL, json=req, headers={"X-Application-Id": APP_ID, "X-Api-Key": API_KEY}
    ).json()
    print(resp_json)
    trailhead_map = {trailhead.node.osm_id: trailhead for trailhead in target_locations}
    ret = {}
    for location in resp_json["results"][0]["locations"]:
        osm_id = int(location["id"])
        ret[trailhead_map[osm_id]] = location["properties"][0]["travel_time"]
    return ret

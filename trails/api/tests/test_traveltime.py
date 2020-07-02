import pytest

from api.models import Trailhead, Node, Point
from api.traveltime import get_travel_times, get_travel_times_cached
from osm.model import Node as ONode

@pytest.mark.django_db
def test_traveltime_api(requests_mock):
    mock_response = '{"results": [{"search_id": "main", "locations": [{"id": "65356597", "properties": [{"travel_time": 1755}]}, {"id": "2557114842", "properties": [{"travel_time": 1098}]}], "unreachable": []}]}'
    requests_mock.post(
        "https://api.traveltimeapp.com/v4/time-filter", text=mock_response
    )
    trailheads = [
        Trailhead(
            id=0,
            node=Node.from_osm_node(
                ONode(id=65356597, lat=37.4303385, lon=-122.313545)
            ),
            name="Skyline Boulevard",
        ),
        Trailhead(
            id=1,
            node=Node.from_osm_node(
                ONode(id=2557114842, lat=37.430213, lon=-122.2886059)
            ),
            name="Patrol Road",
        ),
    ]
    res = get_travel_times_cached(
        Point(x=37.47461, y=-122.23128), target_locations=trailheads
    )
    assert res.keys() == set(trailheads)

    # ensure we hit the cache
    requests_mock.post("https://api.traveltimeapp.com/v4/time-filter", text="")

    res = get_travel_times_cached(
        Point(x=37.47461, y=-122.23128), target_locations=trailheads
    )
    assert res.keys() == set(trailheads)

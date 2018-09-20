from pathlib import Path

import pytest
from gmplot import gmplot
from pytest import fixture

from osm.loader import (
    OsmiumTrailLoader,
    OSMIngestor,
    find_loops_from_root,
    IngestSettings,
)


@fixture
def test_data():
    yield Path(__file__).parent / "data"


@fixture
def huddart_trails(test_data):
    loader = OsmiumTrailLoader()
    loader.apply_file(str(test_data / "huddart.osm"), locations=True)
    yield loader


def test_loader(huddart_trails):
    trails = huddart_trails.trails
    assert len(trails) == 94
    trail_names = {trail.name for _, trail in trails.items()}
    expected = {
        "Miramontes Trail",
        "Dean Trail",
        "Grabtown Gulch Trail",
        "Archery Fire Road",
        "Summit Spring",
        "Crystal Springs Trail",
        "Trail8",
        "Trail11 Bypass",
        "Richards Road",
        "Bear Gulch Trail",
        "Lonely Trail",
        "Chinquapin Trail",
        "Chapparal Trail",
        "Trail7",
        "Bay Area Ridge Trail",
        "Campground Trail",
        "unamed",
        "Purisima Creek Trail",
        "Redwood Trail",
        "Harkins Ridge Trail",
        "Kings Mountain Trail",
        "Borden Hatch Mill Trail",
        "Craig Britton Trail",
        "Bay Tree Trail",
        "North Ridge Trail",
        "Raymundo Trail",
        "Mount Redondo Trail",
        "Sculpture Garden Trail",
        "Skyline Trail",
        "Trail12",
        "Trail6",
    }
    assert trail_names == expected


TestSettings = IngestSettings(max_segments=10, max_distance_km=10, max_concurrent=10)


def test_trail_network(test_data, huddart_trails):
    ingestor = OSMIngestor(TestSettings)
    ingestor.ingest_file(test_data / "huddart.osm")
    networks = list(ingestor.trail_networks())
    assert len(networks) == 1
    matching = [
        network for network in networks if "Miramontes Trail" in network.trail_names()
    ]
    assert len(matching) == 1
    huddart = matching[0]
    assert huddart.total_length_km() == pytest.approx(58.38, rel=0.1)
    gmap = gmplot.GoogleMapPlotter(37.4684697, -122.2895862, 13)

    # Node in the center of the park on a service road
    for trailhead in huddart.trailheads:
        print("marking", trailhead)
        gmap.marker(trailhead.node.lat, trailhead.node.lon, title=trailhead.node.id)

    for trail in huddart.trail_segments():
        trail.draw(gmap)
    gmap.draw("out.html")
    trailhead_ids = [trailhead.node.id for trailhead in huddart.trailheads]

    # On a "service" road that is accessible [access=permissive]
    assert 534963194 in trailhead_ids

    # In the middle of the woods [motor_vehicle=no]
    assert 534042107 not in trailhead_ids

    # highway=steps
    assert 462124623 not in trailhead_ids

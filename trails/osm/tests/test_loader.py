from pathlib import Path

import pytest
# from gmplot import gmplot
from measurement.measures import Distance
from pytest import fixture

from osm.loader import (
    OsmiumTrailLoader,
    OSMIngestor,
    IngestSettings,
    DefaultQualitySettings)
from osm.model import Node, ElevationChange


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
        None,
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


TestSettings = IngestSettings(
    max_segments=20,
    max_distance=Distance(km=20),
    max_concurrent=10,
    trailhead_distance_threshold=Distance(m=300),
    quality_settings=DefaultQualitySettings,
)

ProdLikeSettings = IngestSettings(max_distance=Distance(km=50),
                                  max_segments=300,
                                  max_concurrent=40,
                                  quality_settings=DefaultQualitySettings)


def test_trail_network(test_data, huddart_trails):
    ingestor = OSMIngestor(TestSettings)
    ingestor.load_osm(test_data / "huddart.osm", no_road_crossings=False)
    networks = list(ingestor.trail_networks())
    assert len(networks) == 1
    matching = [
        network for network in networks if "Miramontes Trail" in network.trail_names()
    ]
    assert len(matching) == 1
    huddart = matching[0]

    assert huddart.total_length_km() == pytest.approx(58.38, rel=0.1)
    trailhead_ids = [trailhead.node.id for trailhead in huddart.trailheads]

    # On a "service" road that is accessible [access=permissive]
    assert 534963194 in trailhead_ids

    # In the middle of the woods [motor_vehicle=no]
    assert 534042107 not in trailhead_ids

    # highway=steps
    assert 462124623 not in trailhead_ids


def test_road_splitting(test_data):
    ingestor = OSMIngestor(TestSettings)
    ingestor.load_osm(test_data / "walden-pond.osm")
    networks = list(ingestor.trail_networks())
    assert len(networks) == 3


def test_sidewalk_filter(test_data):
    ingestor = OSMIngestor(TestSettings)
    ingestor.load_osm(test_data / "sidewalks.osm")
    networks = list(ingestor.trail_networks())
    assert len(networks) == 0


def test_trailhead_cap(test_data):
    ingestor = OSMIngestor(TestSettings)
    ingestor.load_osm(test_data / "gg-park.osm")
    networks = list(ingestor.trail_networks())
    assert networks[0].num_clustered < 20
    assert len(networks[0].trailheads) < 20


def test_amenity_parking(test_data):
    ingestor = OSMIngestor(ProdLikeSettings)
    ingestor.load_osm(test_data / "catalina.osm")
    catalina = [t for t in ingestor.trail_networks() if t.total_length_km() > 100][0]
    assert catalina.name == 'Catalina State Park'
    trailhead_ids = {th.node.id for th in catalina.trailheads}
    assert 3199297117 in trailhead_ids


def dont_test_elevation_change():
    home = Node(id=0, lat=37.47463, lon=-122.23131)
    assert home.elevation() == 7
    windy_hill = Node(id=1, lat=37.3646627, lon=-122.246078)
    assert windy_hill.elevation() == 575

    assert ElevationChange.from_nodes(
        [home, home, windy_hill, windy_hill, home]
    ) == ElevationChange(gain=568, loss=568)

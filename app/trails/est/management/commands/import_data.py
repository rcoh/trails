import pickle
from datetime import datetime, timedelta

import pickle
from datetime import datetime, timedelta

import djclick as click
import gpxpy
import gpxpy.gpx
from django.contrib.gis.geos import MultiLineString, LineString
from measurement.measures import Distance

import est.models as e
from osm.loader import IngestSettings, DefaultQualitySettings, OSMIngestor


def circuit_to_gpx(circuit, edge_map):
    gpx = gpxpy.gpx.GPX()

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    # Create first segment in our GPX track:

    # Create points:
    t = datetime.now()
    for i, segment in enumerate(circuit):
        start, end, _, meta = segment
        nodes = edge_map[meta['id']]
        if int(end) == nodes[0].id:
            nodes = reversed(nodes)
        for node in nodes:
            t += timedelta(seconds=1)
            gpx_segment.points.append(
                gpxpy.gpx.GPXTrackPoint(latitude=node.lat, longitude=node.lon, time=t)
            )
    return gpx


@click.command()
@click.argument('osm-data', type=click.Path(exists=True))
def postman(osm_data):
    Settings = IngestSettings(
        max_distance=Distance(km=50),
        max_segments=300,
        max_concurrent=40,
        quality_settings=DefaultQualitySettings,
        location_filter=None,
    )
    loader = OSMIngestor(Settings)
    loader.load_osm(osm_data, extra_links=[(885729040, 827103027)])
    e.TrailNetwork.objects.all().delete()
    for network in loader.trail_networks():
        multiline_strs = MultiLineString([LineString(trail.points()) for trail in network.trail_segments()])

        border = multiline_strs.convex_hull
        simplified = multiline_strs.simplify(tolerance=0.01)
        # TODO: look for polygons that intersect this one
        e.TrailNetwork.objects.create(
            name=network.name,
            trails=simplified,
            bounding_box=border,
            total_length=network.total_length(),
            graph=pickle.dumps(network.graph)
        )




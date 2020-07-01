import collections
import csv
from datetime import datetime, timedelta

import djclick as click
import gmplot as gmplot
import gpxpy
import gpxpy.gpx
from measurement.measures import Distance
from networkx.readwrite import sparse6, nx_yaml, write_gpickle, read_gpickle

from osm.loader import IngestSettings, DefaultQualitySettings, OSMIngestor
from postman_problems.solver import cpp
from postman_problems.stats import calculate_postman_solution_stats

from osm.model import Trail


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
    # s = datetime.now()
    # data = write_gpickle(loader.global_graph, 'test.pickle') #nx_yaml.write_yaml(loader.global_graph, 'test.yaml')
    # e = datetime.now()
    # print(e-s)

    # s = datetime.now()
    # graph = read_gpickle('test.pickle')
    # e = datetime.now()
    # print(e-s)
    # import pdb; pdb.set_trace()
    for i, network in enumerate(loader.trail_networks()):
        print(network.name, network.total_length().mi)
        print(network.trail_names())
        gmap = gmplot.GoogleMapPlotter(42.385, -71.083, 13)
        edge_map = {}
        for segment in network.trail_segments():
            segment.draw(gmap)
            edge_map[segment.id] = segment.nodes
        clean_name = (network.name or f'no-name-{i}').replace(' ', '').replace("\'", '')
        gmap.draw(f"{clean_name}-{i}.html")
        with open('edges.csv', 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=['start', 'end', 'id', 'distance'])
            writer.writeheader()
            for segment in network.trail_segments():
                writer.writerow(dict(start=segment.nodes[0].id, end=segment.nodes[-1].id, id=segment.id,
                                     distance=segment.length_m()))

        try:
            s = datetime.now()
            circuit, graph = cpp('edges.csv')
            e = datetime.now()
            print(f'Time: {e-s}')
            for k, v in calculate_postman_solution_stats(circuit).items():
                print(k, v)
            with open(f"{clean_name}-{i}.gpx", "w") as f:
                f.write(circuit_to_gpx(circuit, edge_map).to_xml())
        except Exception as ex:
            print(ex)

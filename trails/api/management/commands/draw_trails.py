import multiprocessing
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Dict

import djclick as click
from gmplot import gmplot

from api.models import TrailNetwork, Route, Trailhead, Node, TravelCache
from osm.loader import OSMIngestor, IngestSettings, DefaultQualitySettings, LocationFilter, OsmiumTrailLoader
from tqdm import tqdm

@click.command()
@click.argument("file")
@click.option('--center', type=click.STRING)
@click.option('--radius', type=click.INT)
@click.option('--output-file', type=click.STRING, default='out.html')
def draw_trails(file: str, center, radius, output_file):
    start_time = time.time()
    if center:
        lat, lon = center.split(',')
        if radius is None:
            click.secho('Radius must be specified with lat/lon', fg='red')
            exit(1)
        location_filter = LocationFilter(float(lat), float(lon), radius_km=radius)
    else:
        location_filter = None
    trail_loader = OsmiumTrailLoader(location_filter)
    trail_loader.apply_file(file, locations=True)
    gmap = gmplot.GoogleMapPlotter(37.4684697, -122.2895862, 13)
    for _, trail in trail_loader.trails.items():
        trail.draw(gmap)

    gmap.draw(output_file)

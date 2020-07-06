import pickle
from datetime import datetime, timedelta
from multiprocessing import Pool

import djclick as click
import gpxpy
import gpxpy.gpx
from django.contrib.gis.geos import MultiLineString, LineString, MultiPolygon, Polygon, MultiPoint
import gmplot as gmplot
from measurement.measures import Distance
from tqdm import tqdm

import est.models as e
from osm.loader import IngestSettings, DefaultQualitySettings, OSMIngestor


@click.command()
@click.argument('osm-data', type=click.Path(exists=True))
@click.option('--parallelism', '-p', type=click.INT, default=1)
@click.option('--resume/--no-result', default=False)
def import_data(osm_data, resume, parallelism):
    Settings = IngestSettings(
        max_distance=Distance(km=50),
        max_segments=300,
        max_concurrent=40,
        quality_settings=DefaultQualitySettings,
        location_filter=None,
    )
    if not resume:
        e.Import.objects.all().update(active=False)
        import_obj = e.Import(active=True, border=Polygon(), name=str(osm_data))
        import_obj.save()
        digests = set()
    else:
        import_obj = e.Import.objects.order_by('-updated_at').first()
        if not click.confirm(
                f'Resuming import {import_obj.name}, last modified {import_obj.updated_at} currently containing {import_obj.networks.count()} trail networks'):
            return 1
        # TODO: probably n queries
        digests = {n.digest for n in import_obj.networks.all()}
    print(f'{len(digests)} loaded')
    loader = OSMIngestor(Settings)
    loader.load_osm(osm_data, extra_links=[(885729040, 827103027)])
    networks = []
    for network in tqdm(loader.trail_networks(already_processed=digests)):
        try:
            multiline_strs = MultiLineString([LineString(trail.points()) for trail in network.trail_segments()])

            border = multiline_strs.convex_hull
            simplified = multiline_strs  # .simplify(tolerance=0.01)
            if isinstance(simplified, LineString):
                simplified = MultiLineString([simplified])
            # TODO: look for polygons that intersect this one

            trailheads = MultiPoint([t.node.to_point() for t in network.trailheads])

            est_network = e.TrailNetwork(
                name=network.name or '',
                source=import_obj,
                trails=simplified,
                poly=border,
                total_length=network.total_length(),
                graph=pickle.dumps(network.graph),
                trailheads=trailheads,
                digest=network.digest
            )
            est_network.save()
            networks.append(est_network)
        except Exception as ex:
            import pdb;
            pdb.set_trace()
            print(ex)
    if networks:
        import_border = MultiPolygon([n.poly for n in networks])
        import_obj.border = import_border.convex_hull
        import_obj.save()

import hashlib
import os
import pickle
import subprocess
from multiprocessing import Pool

import djclick as click
from django.contrib.gis.geos import MultiLineString, LineString, MultiPolygon, Polygon, MultiPoint
from measurement.measures import Distance
from tqdm import tqdm

import est.models as e
from osm import util
from osm.loader import IngestSettings, DefaultQualitySettings, OSMIngestor

BASE_URL = 'https://download.geofabrik.de/north-america/us/{}-latest.osm.pbf'


def import_state(state):
    print(f'Processing {state}')
    cleaned = state.strip().lower().replace(' ', '-')
    output = f'/osm/logs/{cleaned}.log'
    data_path = f'/osm/{cleaned}.osm.pbf'
    if not os.path.exists(data_path):
        subprocess.run(['curl', BASE_URL.format(cleaned), '-o', data_path], capture_output=True)
    with open(output, 'w') as out:
        subprocess.run(['python', 'manage.py', 'import_data', '--file', data_path], stdout=out)
    return state


def import_states_file(states_file):
    with open(states_file) as f:
        states = [(s,) for s in f.readlines()]

    p = Pool(processes=6)

    for state in util.pmap(states, import_state, p):
        print(f'Finished {state}')


@click.command()
@click.option('--file', type=click.Path(exists=True))
@click.option('--states', type=click.Path(exists=True))
@click.option('--parallelism', '-p', type=click.INT, default=1)
@click.option('--resume/--no-result', default=False)
def import_data(file, resume, states, parallelism):
    if file:
        import_from_file(file, resume)
    if states:
        import_states_file(states)


def sha256_digest(f):
    return subprocess.run(["sha256sum", f], capture_output=True).stdout.split()[0].strip()


def import_from_file(osm_data, resume: bool):
    Settings = IngestSettings(
        max_distance=Distance(km=50),
        max_segments=300,
        max_concurrent=40,
        quality_settings=DefaultQualitySettings,
        location_filter=None,
    )
    digest = sha256_digest(osm_data)
    print('Digest: ', digest)
    if not resume:
        if e.Import.objects.filter(sha256_sum=digest, complete=True):
            print('Import already done!')
            return
        e.Import.objects.all().update(active=False)
        import_obj = e.Import(active=True, complete=False, border=Polygon(), name=str(osm_data), sha256_sum=digest)
        import_obj.save()
        digests = set()
    else:
        import_obj = e.Import.objects.filter(complete=False, sha256_sum=digest).order_by('-updated_at').first()
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
    import_obj.complete = True
    if networks:
        import_border = MultiPolygon([n.poly for n in networks])
        import_obj.border = import_border.convex_hull
        import_obj.save()

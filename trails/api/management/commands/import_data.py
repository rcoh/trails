import multiprocessing
import os
import pickle
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Dict

import djclick as click

from api.models import TrailNetwork, Route, Trailhead, Node, TravelCache
from osm.loader import OSMIngestor, IngestSettings, DefaultQualitySettings, LocationFilter, OsmiumTrailLoader
from tqdm import tqdm



@click.command()
@click.option("--parallelism", "-p", type=click.INT, default=multiprocessing.cpu_count())
@click.option('--center', type=click.STRING)
@click.option('--radius', type=click.INT)
@click.option('--reset', type=click.BOOL, help='Delete all data before importing', default=False)
@click.option('--pickle-dir', type=click.STRING, default='/trail-data/backups')
@click.argument("file", type=click.Path(exists=True))
def import_data(file: str, center, radius, parallelism, reset, pickle_dir):
    start_time = time.time()
    if center:
        lat, lon = center.split(',')
        if radius is None:
            click.secho('Radius must be specified with lat/lon', fg='red')
            exit(1)
        location_filter = LocationFilter(float(lat), float(lon), radius_km=radius)
    else:
        location_filter = None

    Settings = IngestSettings(
        max_distance_km=50,
        max_segments=300,
        max_concurrent=40,
        quality_settings=DefaultQualitySettings,
        location_filter=location_filter
    )


    path = Path(file)
    os.makedirs(pickle_dir, exist_ok=True)
    if location_filter:
        backup_file = Path(pickle_dir) / f'{location_filter.digest()}-{path.name}.pickle'
    else:
        backup_file = Path(pickle_dir) / f'{path.name}.pickle'
    if backup_file.exists():
        result = pickle.load(open(backup_file, 'rb'))
    else:
        loader = OSMIngestor(Settings)
        loader.ingest_file(path, parallelism=parallelism)
        result = loader.result()
        with open(backup_file, 'wb') as f:
            pickle.dump(result, f)
    ingest_time = time.time()
    click.secho(
        f"OSM data [loops: {result.total_loops()}, trail networks: {len(result.loops.keys())}] ingested in {ingest_time-start_time} seconds"
    )

    if reset:
        # Need to delete everything before import TODO
        Trailhead.objects.all().delete()
        Route.objects.all().delete()
        TrailNetwork.objects.all().delete()
        Node.objects.all().delete()
        TravelCache.objects.all().delete()

    trailheads: Dict[int, Trailhead] = {}
    p = Pool(parallelism)
    for trail_network_osm, loops in tqdm(result.loops.items()):
        tn = TrailNetwork.from_osm_trail_network(trail_network_osm)
        TrailNetwork.objects.filter(unique_id=tn.unique_id).delete()
        tn.save()
        for trailhead_osm in tqdm(trail_network_osm.trailheads, desc="Trailheads"):
            n = Node.from_osm_node(trailhead_osm.node)
            n.save()
            Trailhead.objects.filter(node__osm_id=n.osm_id).delete()
            trailhead = Trailhead(trail_network=tn, node=n, name=trailhead_osm.name)
            trailheads[trailhead_osm.node.id] = trailhead

        used_trailheads = {loop.start_node.id: trailheads[loop.start_node.id] for loop in loops}
        tqdm.write(f'Used trailheads: {len(used_trailheads)}/{len(trailheads)}.')
        for trailhead in used_trailheads.values():
            trailhead.save()
        with_trailheads = [(loop, tn, trailheads[loop.start_node.id]) for loop in loops]
        routes = p.starmap(Route.from_subpath, with_trailheads)
        Route.objects.bulk_create(routes)

    end_time = time.time()
    click.secho(
        f"{Route.objects.count()}/{TrailNetwork.objects.count()}/{Trailhead.objects.count()} objects imported in {(end_time-start_time)} seconds"
    )

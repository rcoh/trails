import multiprocessing
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Dict

import djclick as click

from api.models import TrailNetwork, Route, Trailhead, Node
from osm.loader import OSMIngestor, IngestSettings, DefaultQualitySettings
from tqdm import tqdm

Settings = IngestSettings(
    max_distance_km=50,
    max_segments=50,
    max_concurrent=100,
    quality_settings=DefaultQualitySettings,
)


@click.command()
@click.option("--parallelism", "-p", type=click.INT)
@click.argument("file", type=click.Path(exists=True))
def import_data(file: str, parallelism=multiprocessing.cpu_count()):
    start_time = time.time()
    path = Path(file)
    loader = OSMIngestor(Settings)
    loader.ingest_file(path, parallelism=parallelism)
    result = loader.result()
    ingest_time = time.time()
    click.secho(
        f"OSM data [loops: {result.total_loops()}, trail networks: {len(result.loops.keys())}] ingested in {ingest_time-start_time} seconds"
    )

    # Need to delete everything before import TODO
    Trailhead.objects.all().delete()
    Route.objects.all().delete()
    TrailNetwork.objects.all().delete()
    Node.objects.all().delete()

    trailheads: Dict[int, Trailhead] = {}
    for trail_network_osm, loops in tqdm(result.loops.items()):
        tn = TrailNetwork.from_osm_trail_network(trail_network_osm)
        tn.save()
        for trailhead_osm in tqdm(trail_network_osm.trailheads, desc="Trailheads"):
            n = Node.from_osm_node(trailhead_osm.node)
            n.save()
            trailhead = Trailhead(trail_network=tn, node=n, name=trailhead_osm.name)
            trailhead.save()
            trailheads[trailhead_osm.node.id] = trailhead

        with_trailheads = [(loop, tn, trailheads[loop.start_node.id]) for loop in loops]
        p = Pool(parallelism)
        routes = p.starmap(Route.from_subpath, with_trailheads)
        Route.objects.bulk_create(routes)

    end_time = time.time()
    click.secho(
        f"{Route.objects.count()}/{TrailNetwork.objects.count()}/{Trailhead.objects.count()} objects imported in {(end_time-start_time)} seconds"
    )

import time
from pathlib import Path
from typing import Dict

import djclick as click

from api.models import TrailNetwork, Route, Trailhead, Node
from osm.loader import OSMIngestor, IngestSettings
from tqdm import tqdm

Settings = IngestSettings(max_distance_km=50, max_segments=20, max_concurrent=50)

@click.command()
@click.argument('file', type=click.Path(exists=True))
def import_data(file: str):
    start_time = time.time()
    path = Path(file)
    loader = OSMIngestor(Settings)
    loader.ingest_file(path)
    result = loader.result()
    ingest_time = time.time()
    click.secho(f'OSM data [loops: {result.total_loops()}, trail networks: {len(result.loops.keys())}] ingested in {ingest_time-start_time} seconds')

    # Need to delete everything before import TODO
    Trailhead.objects.all().delete()
    Route.objects.all().delete()
    TrailNetwork.objects.all().delete()
    Node.objects.all().delete()

    trailheads: Dict[int, Trailhead] = {}
    for trail_network_osm, loops in tqdm(result.loops.items()):
        tn = TrailNetwork.from_osm_trail_network(trail_network_osm)
        tn.save()
        for trailhead_osm in trail_network_osm.trailheads:
            n = Node.from_osm_node(trailhead_osm)
            n.save()
            trailhead = Trailhead(trail_network=tn, node=n)
            trailhead.save()
            trailheads[trailhead_osm.id] = trailhead

        for loop in loops:
            trailhead = trailheads[loop.start_node.id]
            Route.from_subpath(loop, tn, trailhead).save()

    end_time = time.time()
    click.secho(f'{Route.objects.count()}/{TrailNetwork.objects.count()}/{Trailhead.objects.count()} objects imported in {(end_time-start_time)} seconds')

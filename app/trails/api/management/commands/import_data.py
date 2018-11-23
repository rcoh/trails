import datetime
import json
import multiprocessing
import os
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple

import djclick as click
from measurement.measures import Distance

from api.models import TrailNetwork, Route, Trailhead, Node, TravelCache
from osm import util
from osm.loader import (
    OSMIngestor,
    IngestSettings,
    DefaultQualitySettings,
    LocationFilter,
)
import tracemalloc

from osm.model import Subpath

snapshots = []


def collect_stats(self):
    snapshots.append(tracemalloc.take_snapshot())
    if len(self.snapshots) > 1:
        stats = self.snapshots[-1].compare_to(self.snapshots[-2], "filename")

        for stat in stats[:10]:
            print(
                "{} new KiB {} total KiB {} new {} total memory blocks: ".format(
                    stat.size_diff / 1024, stat.size / 1024, stat.count_diff, stat.count
                )
            )
            for line in stat.traceback.format():
                print(line)


@click.command()
@click.option(
    "--parallelism", "-p", type=click.INT, default=multiprocessing.cpu_count()
)
@click.option("--center", type=click.STRING)
@click.option("--radius", type=click.INT)
@click.option(
    "--reset", type=click.BOOL, help="Delete all data before importing", default=False
)
@click.option("--pickle-dir", type=click.STRING, default="/trail-data/backups")
@click.option("--meta-dir", type=click.STRING, default="/trail-data/ingest-metadata")
@click.argument("file", type=click.Path(exists=True))
def import_data(
        file: str,
        center,
        radius,
        parallelism,
        reset,
        pickle_dir,
        meta_dir,
):
    start_time = time.time()
    location_filter: Optional[LocationFilter] = None
    if center:
        lat, lon = center.split(",")
        if radius is None:
            click.secho("Radius must be specified with lat/lon", fg="red")
            exit(1)
        location_filter = LocationFilter(float(lat), float(lon), radius_km=radius)

    Settings = IngestSettings(
        max_distance=Distance(km=50),
        max_segments=300,
        max_concurrent=40,
        quality_settings=DefaultQualitySettings,
        location_filter=location_filter,
    )

    path = Path(file)
    os.makedirs(pickle_dir, exist_ok=True)
    loader = OSMIngestor(Settings)
    if location_filter:
        ingest_id = f"{location_filter.digest()}-{path.name}"
    else:
        ingest_id = f"unfiltered-{path.name}"

    nested_meta_dir = Path(meta_dir) / ingest_id
    os.makedirs(nested_meta_dir, exist_ok=True)
    metadata_file = nested_meta_dir / f"{datetime.datetime.utcnow().isoformat()}.json"

    if reset:
        # Need to delete everything before import TODO
        Trailhead.objects.all().delete()
        Route.objects.all().delete()
        TrailNetwork.objects.all().delete()
        Node.objects.all().delete()
    TravelCache.objects.all().delete()

    p = Pool(parallelism)
    metadata: Dict[str, Dict[int, Dict[Any, Any]]] = {}
    routes_import = 0
    trailheads_imported = 0
    for network_result in loader.ingest_file(path, parallelism=parallelism):
        trail_network_osm = network_result.trail_network
        trailhead_dict = network_result.loops
        if network_result.total_loops() == 0:
            continue
        tn = TrailNetwork.from_osm_trail_network(trail_network_osm)
        TrailNetwork.objects.filter(unique_id=tn.unique_id).delete()
        tn.save()
        routes_for_network: List[Tuple[Subpath, TrailNetwork, Trailhead]] = []
        metadata[tn.unique_id] = {}
        for trailhead_osm, trailhead_result in trailhead_dict.items():
            try:
                if trailhead_result.meta.num_loops == 0:
                    continue
                n = Node.from_osm_node(trailhead_osm.node)
                n.save()
                Trailhead.objects.filter(node__osm_id=n.osm_id).delete()
                trailhead = Trailhead(
                    trail_network=tn, node=n, name=trailhead_osm.name[:32]
                )
                if trailhead_result.loops:
                    trailheads_imported += 1
                    trailhead.save()
                    routes_for_network += [
                        (loop, tn, trailhead) for loop in trailhead_result.loops
                    ]
                metadata[tn.unique_id][
                    trailhead_osm.node.id
                ] = trailhead_result.meta._asdict()
            except Exception as ex:
                print("Error importing trailhead", ex)

        if len(routes_for_network) > 0:
            routes = util.pmap(routes_for_network, Route.from_subpath, p)
            Route.objects.bulk_create(routes)
            routes_import += len(routes)

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    end_time = time.time()
    click.secho(
        f"{routes_import}/{TrailNetwork.objects.count()}/{trailheads_imported} objects imported in {(end_time-start_time)} seconds"
    )

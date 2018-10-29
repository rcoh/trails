import datetime
import json
import multiprocessing
import os
import pickle
import time
from multiprocessing.pool import Pool
from pathlib import Path

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
from tqdm import tqdm


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
@click.option("--recompute-loops", type=click.BOOL, default=True)
@click.option("--no-cache", type=click.BOOL, default=False)
@click.argument("file", type=click.Path(exists=True))
def import_data(
    file: str,
    center,
    radius,
    parallelism,
    reset,
    pickle_dir,
    recompute_loops,
    meta_dir,
    no_cache,
):
    start_time = time.time()
    if center:
        lat, lon = center.split(",")
        if radius is None:
            click.secho("Radius must be specified with lat/lon", fg="red")
            exit(1)
        location_filter = LocationFilter(float(lat), float(lon), radius_km=radius)
    else:
        location_filter = None

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

    backup_file = (Path(pickle_dir) / ingest_id).with_suffix(".pickle")

    nested_meta_dir = Path(meta_dir) / ingest_id
    os.makedirs(nested_meta_dir, exist_ok=True)
    metadata_file = nested_meta_dir / f"{datetime.datetime.utcnow().isoformat()}.json"
    if backup_file.exists() and not no_cache:
        result = pickle.load(open(backup_file, "rb"))
        if recompute_loops:
            loader.recompute_loops(result, parallelism)
            result = loader.result()
    else:
        loader.ingest_file(path, parallelism=parallelism)
        result = loader.result()
        with open(backup_file, "wb") as f:
            pickler = pickle.Pickler(f)
            pickler.fast = True
            pickler.dump(result)
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

    p = Pool(parallelism)
    metadata = {}
    routes_import = 0
    trailheads_imported = 0
    for trail_network_osm, trailhead_dict in tqdm(result.metaloops.items()):
        tn = TrailNetwork.from_osm_trail_network(trail_network_osm)
        TrailNetwork.objects.filter(unique_id=tn.unique_id).delete()
        tn.save()
        routes_for_network = []
        metadata[tn.unique_id] = {}
        for trailhead_osm, trailhead_result in tqdm(
            trailhead_dict.items(), desc="Trailheads"
        ):
            n = Node.from_osm_node(trailhead_osm.node)
            n.save()
            Trailhead.objects.filter(node__osm_id=n.osm_id).delete()
            trailhead = Trailhead(trail_network=tn, node=n, name=trailhead_osm.name)
            if trailhead_result.loops:
                trailheads_imported += 1
                trailhead.save()
                routes_for_network += [
                    (loop, tn, trailhead) for loop in trailhead_result.loops
                ]
            metadata[tn.unique_id][
                trailhead_osm.node.id
            ] = trailhead_result.meta._asdict()

        routes = util.pmap(routes_for_network, Route.from_subpath, p)
        print(f"Creating routes {len(routes)}")
        Route.objects.bulk_create(routes)
        routes_import += len(routes)

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    end_time = time.time()
    click.secho(
        f"{routes_import}/{TrailNetwork.objects.count()}/{trailheads_imported} objects imported in {(end_time-start_time)} seconds"
    )

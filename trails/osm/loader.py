import itertools
import random
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List, Dict, NamedTuple, Iterator, Optional, Set

import collections
import geopy.distance
import networkx as nx
import osmium as o
from tqdm import tqdm

from osm.model import Trail, InverseGraph, TrailNetwork, Subpath, Trailhead, Node
from osm.util import verify_identical_nodes

TRAIL = {"path", "footway", "track", "trail", "pedestrian", "steps"}
INACCESSIBLE = {"service"}
BAD_FOOTWAYS = {"sidewalk", "crossing"}

def is_trail(way):
    trail_like = way.tags["highway"] in TRAIL
    if trail_like and way.tags.get('footway') in BAD_FOOTWAYS:
        return False
    return trail_like



def drivable(way):
    # TODO: learn these features / rules engine?
    no_cars = way.tags.get("motor_vehicle") in ["no"]
    accessible = way.tags.get("access") in ["yes", "permissive", None]
    return not is_trail(way) and accessible and not no_cars

class LocationFilter(NamedTuple):
    lat: float
    lon: float
    radius_km: float

    def tup(self):
        return (self.lat, self.lon)

class OsmiumTrailLoader(o.SimpleHandler):
    def __init__(self, location_filter: Optional[LocationFilter]=None):
        super(OsmiumTrailLoader, self).__init__()
        self.trails: Dict[int, Trail] = {}
        self.non_trail_nodes: Dict[int, str] = {}
        self.location_filter = location_filter

    def way(self, w):
        if "highway" in w.tags:
            if self.location_filter:
                first_node = w.nodes[0]
                start = first_node.lat, first_node.lon
                dist_from_here = geopy.distance.great_circle(self.location_filter.tup(), start).km
                if dist_from_here > self.location_filter.radius_km:
                    return
            if is_trail(w):
                try:
                    self.trails[w.id] = Trail.from_way(w)
                except o.InvalidLocationError:
                    # A location error might occur if the osm file is an extract
                    # where nodes of ways near the boundary are missing.
                    print("WARNING: way %d incomplete. Ignoring." % w.id)
            if drivable(w):
                node_ids = {n.ref: w.tags.get("name", "No name") for n in w.nodes}
                self.non_trail_nodes.update(node_ids)


class OsmLoadResult(NamedTuple):
    trail_networks: List[TrailNetwork]
    loops: Dict[TrailNetwork, List[Subpath]]

    def total_loops(self):
        return sum([len(l) for l in self.loops.values()])

MIN_QUALITY = .7
def worth_keeping(loop: Subpath):
    if loop.is_pure_out_and_back():
        return True
    else:
        return loop.quality() > MIN_QUALITY

def proc_trailhead(args):
    trailhead, network, settings = args
    new_loops = list(
        find_loops_from_root(
            network,
            trailhead.node,
            max_distance_km=settings.max_distance_km,
            max_concurrent=settings.max_concurrent,
            max_segments=settings.max_segments,
        )
    )
    new_loops = filter_similar(new_loops)
    # TODO: hide bad routes in the UI?
    new_loops = [loop for loop in new_loops if worth_keeping(loop)]
    for loop in new_loops:
        loop.elevation_change()
    return (network, new_loops)


class QualitySettings(NamedTuple):
    repeat_node_weight: int
    min_quality: float = 0.8


class IngestSettings(NamedTuple):
    max_concurrent: int
    max_distance_km: int
    max_segments: int
    quality_settings: QualitySettings
    location_filter: Optional[LocationFilter] = None


DefaultQualitySettings = QualitySettings(repeat_node_weight=1)

DefaultIngestSettings = IngestSettings(
    max_concurrent=1000,
    max_distance_km=50,
    max_segments=50,
    quality_settings=DefaultQualitySettings,
)


class OSMIngestor:
    def __init__(self, ingest_settings: Optional[IngestSettings] = None) -> None:
        if ingest_settings is None:
            ingest_settings = DefaultIngestSettings
        self.ingest_settings = ingest_settings
        self.trails: Dict[int, Trail] = {}
        self.non_trail_nodes: Dict[int, str] = {}
        self.global_graph = nx.Graph()
        self.loops: Dict[TrailNetwork, List[Subpath]] = collections.defaultdict(list)

    def ingest_file(self, filename: Path, parallelism=1):
        # TODO: figure out file bounds, delete data within those bounds
        before_trailheads = set(self.trailheads())
        osm_loader = OsmiumTrailLoader(self.ingest_settings.location_filter)
        osm_loader.apply_file(str(filename), locations=True)
        print(f'Before applying location filter: {len(osm_loader.trails)}')
        trails = self.apply_location_filter(osm_loader.trails)
        print(f'After applying location filter: {len(trails)}')
        self.trails.update(trails)
        self.non_trail_nodes.update(osm_loader.non_trail_nodes)
        self.add_trails_to_graph(trails.values())
        after_trailheads = set(self.trailheads())

        new_trailheads = after_trailheads - before_trailheads
        network_map = self.trailead_network_map()

        trailheads_to_process = [
            (trailhead, network_map[trailhead], self.ingest_settings)
            for trailhead in new_trailheads
        ]

        if parallelism > 1:
            p = Pool(parallelism)
            iter = p.imap_unordered(proc_trailhead, trailheads_to_process, chunksize=10)
        else:
            iter = map(proc_trailhead, trailheads_to_process)

        for (network, loops) in tqdm(iter, total=len(trailheads_to_process)):
            self.loops[network] += loops

    def apply_location_filter(self, trails: Dict[int, Trail]) -> Dict[int, Trail]:
        res = {}
        if self.ingest_settings.location_filter:
            here = (self.ingest_settings.location_filter.lat, self.ingest_settings.location_filter.lon)
            max_dist_km = self.ingest_settings.location_filter.radius_km
            for id, trail in trails.items():
                trail_start = (trail.nodes[0].lat, trail.nodes[0].lon)
                dist_from_here = geopy.distance.great_circle(here, trail_start).km
                if dist_from_here < max_dist_km:
                    res[id] = trail
        else:
            res = trails
        return res

    def result(self) -> OsmLoadResult:
        tn: List[TrailNetwork] = list(self.trail_networks())
        nodes: Set[Node] = set()
        for trail in self.trails.values():
            nodes.update(trail.nodes)

        return OsmLoadResult(list(self.trail_networks()), loops=self.loops)

    def add_trails_to_graph(self, new_trails):
        segmented_trails = segment_trails(new_trails)
        G = self.global_graph
        for trail in segmented_trails:
            G.add_node(trail.nodes[0]),
            G.add_node(trail.nodes[-1])
            G.add_edge(
                trail.nodes[0],
                trail.nodes[-1],
                weight=trail.length().km,
                name=trail.name,
                trail=trail,
            )

    def trail_networks(self):
        G = self.global_graph
        for c in nx.connected_components(G):
            subgraph = G.subgraph(c).copy()
            network = TrailNetwork(subgraph, self.non_trail_nodes)
            if network.total_length_km() > 5:
                yield network

    def trailead_network_map(self) -> Dict[Trailhead, TrailNetwork]:
        res = {}
        for network in self.trail_networks():
            for trailhead in network.trailheads:
                res[trailhead] = network
        return res

    def trailheads(self) -> Iterator[Trailhead]:
        for network in self.trail_networks():
            for trailhead in network.trailheads:
                yield trailhead

    def write_to_map(self, filename, gmap):
        osm_loader = OsmiumTrailLoader(self.ingest_settings.location_filter)
        osm_loader.apply_file(str(filename), locations=True)
        print(f'Before applying location filter: {len(osm_loader.trails)}')
        trails = self.apply_location_filter(osm_loader.trails)
        for _, trail in trails.items():
            trail.draw(gmap)





def segment_trails(trails: List[Trail]):
    """Returns a new list of trails where all intersections are at the start or end"""
    graph = InverseGraph()
    for trail in trails:
        graph.add_trail(trail)

    flat_trails: List[Trail] = []
    for trail in trails:
        split_idxs = []
        for (i, node) in enumerate(trail.nodes[1:-1], 1):
            if len(graph.node_trail_map[node.id]) > 1:
                split_idxs.append(i)

        if split_idxs:
            flat_trails += trail.split_at(split_idxs)
        else:
            flat_trails.append(trail)
    verify_identical_nodes(trails, flat_trails)
    return flat_trails


def find_loops_from_root(
    trail_network: TrailNetwork,
    root,
    max_segments=20,
    max_distance_km=10,
    max_concurrent=1000,
):
    random.seed(735)
    subgraph = trail_network.graph
    active_paths = [Subpath.from_startnode(root)]
    while active_paths:
        filtered_paths = []
        for path in active_paths:
            if (
                path.length_km < max_distance_km
                and len(path.trail_segments) < max_segments
            ):
                filtered_paths.append(path)
        active_paths = filtered_paths
        final_paths = []
        active_paths = sorted(active_paths, key=lambda path: -1 * path.quality())
        if len(active_paths) > max_concurrent:
            active_paths = [path for path in active_paths if path.quality() > 0.7]
        active_paths = filter_similar(active_paths)
        active_paths = active_paths[:max_concurrent]
        for path in active_paths:
            options = list(dict(subgraph[path.last_node()]).items())
            for next_node, next_trail in options:
                if next_trail["trail"].id == path.trail_segments[-1].id and len(options) > 1:
                    continue
                new_path = path.add_node(next_trail["trail"])
                if new_path.is_complete():
                    yield new_path
                else:
                    final_paths.append(new_path)
        active_paths = final_paths


def filter_similar(subpaths: List[Subpath]):
    to_drop = set()
    for (p1, p2) in itertools.combinations(subpaths, 2):
        # 20% length difference
        if abs((p2.length_km - p1.length_km) / p2.length_km) < .2:
            if p2.similarity(p1) > 0.8:
                to_drop.add(p2)
    assert to_drop == set() or len(to_drop) < len(subpaths), f"{to_drop}, {subpaths}"
    ret = [p for p in subpaths if p not in to_drop]

    return ret

def evaluate_quality_metrics(subpaths: List[Subpath]):
    pass
    # distance histogram
    # elevation histogram
    # similarity metrics
    # quality metrics

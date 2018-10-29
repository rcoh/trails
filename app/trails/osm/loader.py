import hashlib
import itertools
import random
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List, Dict, NamedTuple, Iterator, Optional, Set

import collections
import geopy.distance
import networkx as nx
import osmium as o
from measurement.measures import Distance
from tqdm import tqdm

from osm.model import Trail, InverseGraph, TrailNetwork, Subpath, Trailhead, Node
from osm.util import verify_identical_nodes, window

TRAIL = {"path", "footway", "track", "trail", "pedestrian", "steps"}
INACCESSIBLE = {"service"}
BAD_FOOTWAYS = {"sidewalk", "crossing"}


def is_trail(way):
    trail_like = way.tags["highway"] in TRAIL
    if trail_like and way.tags.get("footway") in BAD_FOOTWAYS:
        return False
    return trail_like


def drivable(way):
    # TODO: learn these features / rules engine?
    no_cars = way.tags.get("motor_vehicle") in ["no"]
    if no_cars:
        return False

    if way.tags.get("access") == "no":
        return False

    accessible = way.tags.get("access") in ["yes", "permissive", None]
    explicitly_accessible = way.tags.get("access") in ["yes", "permissive"]
    service_road = (
            way.tags.get("highway") == "service"
            and way.tags.get("service") != "parking_aisle"
    )
    if service_road and not explicitly_accessible:
        return False
    return not is_trail(way) and accessible and not no_cars


class LocationFilter(NamedTuple):
    lat: float
    lon: float
    radius_km: float

    def tup(self):
        return (self.lat, self.lon)

    def digest(self):
        return hashlib.sha1(
            f"{self.lat}-{self.lon}-{self.radius_km}".encode("ascii")
        ).hexdigest()[:16]


class OsmiumTrailLoader(o.SimpleHandler):
    def __init__(self, location_filter: Optional[LocationFilter] = None):
        super(OsmiumTrailLoader, self).__init__()
        self.trails: Dict[int, Trail] = {}
        self.non_trail_nodes: Dict[int, str] = {}
        self.location_filter = location_filter

    def way(self, w):
        if "highway" in w.tags:
            if self.location_filter:
                first_node = w.nodes[0]
                start = first_node.lat, first_node.lon
                dist_from_here = geopy.distance.great_circle(
                    self.location_filter.tup(), start
                ).km
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


MIN_QUALITY = 0.7


class TrailheadMeta(NamedTuple):
    num_loops: int
    loop_diversity: float
    loop_quality: float
    longest_loop: int
    shortest_loop: int
    network_length: float
    ingest_time: float


class TrailheadResult(NamedTuple):
    loops: List[Subpath]
    meta: TrailheadMeta


class OsmLoadResult(NamedTuple):
    trail_networks: List[TrailNetwork]
    loops: Dict[TrailNetwork, List[Subpath]]
    metaloops: Dict[TrailNetwork, Dict[Trailhead, TrailheadResult]]

    def total_loops(self):
        return sum([len(l) for l in self.loops.values()])


def worth_keeping(loop: Subpath):
    if loop.length_m < SHORTEST_LOOP.m:
        return False
    if loop.is_pure_out_and_back():
        return True
    else:
        return loop.quality() > MIN_QUALITY and loop.num_spurs() < 1


def proc_network(args):
    network, settings = args
    tqdm.write(f"Processing trail network {network}")
    ret: Dict[Trailhead, TrailheadResult] = {}
    for trailhead in network.trailheads:
        start_time = time.time()
        new_loops = list(find_loops_from_root(network, trailhead.node, settings))
        # Produce about 1 loop per 5k of trails
        target_loop_number = int(network.total_length().km // 5)
        new_loops = sorted(new_loops, key=lambda l: -1 * l.quality())
        new_loops = [loop for loop in new_loops if worth_keeping(loop)]
        new_loops = new_loops[: target_loop_number * 3]
        new_loops = filter_similar(new_loops, 0.75)
        # TODO: hide bad routes in the UI?
        for loop in new_loops:
            loop.elevation_change()

        end_time = time.time()
        metadata = meta(network, new_loops, time=end_time - start_time)
        ret[trailhead] = TrailheadResult(new_loops, metadata)
    return (network, ret)


def meta(
        trail_network: TrailNetwork, loops: List[Subpath], time: float
) -> TrailheadMeta:
    num_loops = len(loops)
    if num_loops == 0:
        loop_quality = 0
        loop_diversity = 0
        longest_loop = 0
        shortest_loop = 0
    else:
        loop_quality = sum([loop.quality() for loop in loops]) / num_loops
        pairs = list(itertools.combinations(loops, 2))
        loop_diversity = (
            1
            if not pairs
            else sum([1 - a.similarity(b) for (a, b) in pairs]) / len(pairs)
        )
        longest_loop = max([loop.length_m for loop in loops])
        shortest_loop = min([loop.length_m for loop in loops])
    network_length = trail_network.total_length()
    return TrailheadMeta(
        num_loops=num_loops,
        loop_diversity=loop_diversity,
        shortest_loop=shortest_loop,
        longest_loop=longest_loop,
        network_length=network_length.km,
        loop_quality=loop_quality,
        ingest_time=time,
    )


class QualitySettings(NamedTuple):
    repeat_node_weight: int
    min_quality: float = 0.8


class IngestSettings(NamedTuple):
    max_concurrent: int
    max_distance: Distance
    max_segments: int
    quality_settings: QualitySettings
    location_filter: Optional[LocationFilter] = None
    trailhead_distance_threshold: Distance = Distance(m=300)


DefaultQualitySettings = QualitySettings(repeat_node_weight=1)

DefaultIngestSettings = IngestSettings(
    max_concurrent=1000,
    max_distance=Distance(km=50),
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
        self.trailnetwork_results: Dict[
            TrailNetwork, Dict[Trailhead, TrailheadResult]
        ] = {}

    def recompute_loops(self, results: OsmLoadResult, parallelism: int):
        # process the biggest networks first to take advantage of parallelism
        networks_to_process = sorted(
            [(network, self.ingest_settings) for network in results.trail_networks],
            key=lambda net_set: -1 * net_set[0].total_length_km(),
        )

        if parallelism > 1:
            p = Pool(parallelism)
            iter = p.imap_unordered(proc_network, networks_to_process)
        else:
            iter = map(proc_network, networks_to_process)

        for (network, loops) in tqdm(iter, total=len(networks_to_process)):
            self.trailnetwork_results[network] = loops

    def ingest_file(self, filename: Path, parallelism=1):
        # TODO: figure out file bounds, delete data within those bounds
        osm_loader = OsmiumTrailLoader(self.ingest_settings.location_filter)
        osm_loader.apply_file(str(filename), locations=True)
        trails = osm_loader.trails
        print(f"Importing {len(trails)} trails")
        self.trails.update(trails)
        self.non_trail_nodes.update(osm_loader.non_trail_nodes)
        self.add_trails_to_graph(trails.values())

        networks_to_process = [
            (network, self.ingest_settings) for network in self.trail_networks()
        ]

        if parallelism > 1:
            p = Pool(parallelism)
            iter = p.imap_unordered(proc_network, networks_to_process)
        else:
            iter = map(proc_network, networks_to_process)

        for (network, result) in tqdm(iter, total=len(networks_to_process)):
            yield (network, result)

    def apply_location_filter(self, trails: Dict[int, Trail]) -> Dict[int, Trail]:
        res = {}
        if self.ingest_settings.location_filter:
            here = (
                self.ingest_settings.location_filter.lat,
                self.ingest_settings.location_filter.lon,
            )
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
        nodes: Set[Node] = set()
        for trail in self.trails.values():
            nodes.update(trail.nodes)

        ret = {}
        for k, result in self.trailnetwork_results.items():
            ret[k] = sum([v.loops for v in result.values()], [])

        return OsmLoadResult(
            list(self.trail_networks()), loops=ret, metaloops=self.trailnetwork_results
        )

    def loops(self):
        for _, result in self.trailnetwork_results.items():
            for _, result in result.items():
                for loop in result.loops:
                    yield loop

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
            network = TrailNetwork(
                subgraph,
                self.non_trail_nodes,
                self.ingest_settings.trailhead_distance_threshold,
            )
            if network.total_length() > Distance(km=5):
                yield network

    def trailheads(self) -> Iterator[Trailhead]:
        for network in self.trail_networks():
            for trailhead in network.trailheads:
                yield trailhead


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


SHORTEST_LOOP = Distance(km=3)

def problematic_network(network):
    total_distance = network.total_length()
    subgraph = network.graph
    num_edges = len(subgraph.edges)
    if (total_distance.km / num_edges) < .1:
        return True
    else:
        return False

MAX_SEARCH = 20
def find_loops_from_root(
        trail_network: TrailNetwork, root: Node, settings: IngestSettings
):
    max_segments = settings.max_segments
    max_distance = settings.max_distance
    max_concurrent = settings.max_concurrent
    if problematic_network(trail_network):
        return

    random.seed(735)
    subgraph = trail_network.graph
    num_edges = len(subgraph.edges)

    max_segments = min(num_edges, max_segments)
    max_distance = min(max_distance, trail_network.total_length() * 1.1)
    max_distance_m = max_distance.m
    active_paths = [Subpath.from_startnode(root)]
    stop_searching_thresh = min(max(1, int(trail_network.total_length().km / 4)), 20)
    exit_thresh = min(max(int(trail_network.total_length().km / 2), 1), 20)
    loops_yielded = 0
    s = time.time()
    layers = 0
    while active_paths and loops_yielded < exit_thresh:
        layers += 1
        filtered_paths = []
        for path in active_paths:
            if (
                    path.length_m < max_distance_m
                    and len(path.trail_segments) < max_segments
            ):
                filtered_paths.append(path)
        active_paths = filtered_paths
        final_paths = []
        if len(active_paths) > max_concurrent:
            active_paths = sorted(active_paths, key=lambda path: -1 * path.quality())
            active_paths = [p for p in active_paths if p.quality() > 0.5]
            if loops_yielded < stop_searching_thresh:
                pruned_paths = [p for p in active_paths[max_concurrent:] if p.length_m > SHORTEST_LOOP.m / 2][:MAX_SEARCH]
                for path in pruned_paths:
                    back_to_root = nx.shortest_path(
                        subgraph,
                        source=path.last_node(),
                        target=path.first_node(),
                        weight="weight",
                    )
                    for (n1, n2) in window(back_to_root):
                        edge = subgraph[n1][n2]
                        path = path.add_node(edge["trail"], mutate=True)
                    assert path.is_complete()
                    if worth_keeping(path):
                        loops_yielded += 1
                        yield path
                    if loops_yielded > stop_searching_thresh:
                        break
            # active_paths = filter_similar(active_paths, 0.90)
            active_paths = active_paths[:max_concurrent]
        for path in active_paths:
            options = list(dict(subgraph[path.last_node()]).items())
            for next_node, next_trail in options:
                if (
                        next_trail["trail"].id == path.trail_segments[-1].id
                        and len(options) > 1
                ):
                    continue
                new_path = path.add_node(next_trail["trail"])
                if new_path.is_complete():
                    if worth_keeping(new_path):
                        loops_yielded += 1
                        yield new_path
                else:
                    final_paths.append(new_path)
        active_paths = final_paths


def filter_similar(subpaths: List[Subpath], max_similarity):
    to_drop = set()
    for (p1, p2) in itertools.combinations(subpaths, 2):
        # 20% length difference
        if abs((p2.length_m - p1.length_m) / p2.length_m) < 0.2:
            if p2.similarity(p1) > max_similarity:
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

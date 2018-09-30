import random
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List, Dict, NamedTuple, Iterator, Optional, Set

import collections
import networkx as nx
import osmium as o
from tqdm import tqdm

from osm.model import Trail, InverseGraph, TrailNetwork, Subpath, Trailhead, Node
from osm.util import verify_identical_nodes

TRAIL = {"path", "footway", "track", "trail", "pedestrian", "steps"}
INACCESSIBLE = {"service"}


def is_trail(way):
    return way.tags["highway"] in TRAIL


def drivable(way):
    # TODO: learn these features / rules engine?
    no_cars = way.tags.get("motor_vehicle") in ["no"]
    accessible = way.tags.get("access") in ["yes", "permissive", None]
    return not is_trail(way) and accessible and not no_cars


class OsmiumTrailLoader(o.SimpleHandler):
    def __init__(self):
        super(OsmiumTrailLoader, self).__init__()
        self.trails: Dict[int, Trail] = {}
        self.non_trail_nodes: Dict[int, str] = {}

    def way(self, w):
        if "highway" in w.tags:
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


def proc_trailhead(args):
    trailhead, network_map, settings = args
    network = network_map[trailhead]
    new_loops = list(
        find_loops_from_root(
            network,
            trailhead.node,
            max_distance_km=settings.max_distance_km,
            max_concurrent=settings.max_concurrent,
            max_segments=settings.max_segments,
        )
    )
    for loop in new_loops:
        loop.elevation_change()
    return (network, new_loops)


class IngestSettings(NamedTuple):
    max_concurrent: int
    max_distance_km: int
    max_segments: int


DefaultIngestSettings = IngestSettings(
    max_concurrent=1000, max_distance_km=50, max_segments=50
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
        osm_loader = OsmiumTrailLoader()
        osm_loader.apply_file(str(filename), locations=True)
        self.trails.update(osm_loader.trails)
        self.non_trail_nodes.update(osm_loader.non_trail_nodes)
        self.add_trails_to_graph(osm_loader.trails.values())
        after_trailheads = set(self.trailheads())

        new_trailheads = after_trailheads - before_trailheads
        network_map = self.trailead_network_map()

        p = Pool(parallelism)

        trailheads_to_process = [
            (trailhead, network_map, self.ingest_settings)
            for trailhead in new_trailheads
        ]

        for (network, loops) in tqdm(
            p.imap_unordered(proc_trailhead, trailheads_to_process),
            total=len(trailheads_to_process),
        ):
            self.loops[network] += loops

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
            subgraph = G.subgraph(c)
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
    complete_paths: List[Subpath] = []
    subgraph = trail_network.graph
    active_paths = [Subpath.from_startnode(root)]
    while active_paths:
        filtered_paths = []
        for path in active_paths:
            if (
                path.length_km() < max_distance_km
                and len(path.trail_segments) < max_segments
            ):
                filtered_paths.append(path)
        active_paths = filtered_paths
        final_paths = []
        random.shuffle(active_paths)
        active_paths = active_paths[:max_concurrent]
        for path in active_paths:
            options = list(dict(subgraph[path.last_node()]).items())
            random.shuffle(options)
            for next_node, next_trail in options:
                if next_trail["trail"].id == path.trail_segments[-1].id:
                    continue
                new_path = path.fork()
                is_loop = new_path.add_node(next_trail["trail"])
                if is_loop:
                    yield new_path
                final_paths.append(new_path)
        active_paths = final_paths
    return complete_paths

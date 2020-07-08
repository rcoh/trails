import hashlib
import itertools
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List, Dict, NamedTuple, Iterator, Optional, Set, Tuple

import geopy.distance
import networkx as nx
import osmium as o
from django.contrib.gis.geos import Polygon, MultiPolygon, Point, MultiPoint, GEOSException
from measurement.measures import Distance

from osm import util
from osm.model import Trail, InverseGraph, TrailNetwork, Subpath, Trailhead, Node, NodeId

TRAIL = {"path", "footway", "track", "trail", "pedestrian", "steps"}
INACCESSIBLE = {"service"}
BAD_FOOTWAYS = {"sidewalk", "crossing"}

PARKS = {"park", "nature_reserve"}
PARKISH_BOUNDARIES = {"national_park", "protected_area"}


def is_trail(way):
    trail_like = way.tags["highway"] in TRAIL
    if trail_like and way.tags.get("footway") in BAD_FOOTWAYS:
        return False
    return trail_like


def drivable(way):
    # TODO: learn these features / rules engine?
    if 'highway' in way.tags:
        no_cars = way.tags.get("motor_vehicle") in ["no"]
        if no_cars:
            return False

        if way.tags.get("access") == "no":
            return False

        accessible = way.tags.get("access") in ["yes", "permissive", None]
        service_road = (
                way.tags.get("highway") == "service"
                and way.tags.get("service") != "parking_aisle"
        )
        if service_road and not accessible:
            return False
        return not is_trail(way) and accessible and not no_cars
    else:
        if way.tags.get('amenity') in ['parking']:
            return True
        return False


class LocationFilter(NamedTuple):
    lat: float
    lon: float
    radius_km: float

    def tup(self):
        return self.lat, self.lon

    def digest(self):
        return hashlib.sha1(
            f"{self.lat}-{self.lon}-{self.radius_km}".encode("ascii")
        ).hexdigest()[:16]


class Park(NamedTuple):
    border: MultiPolygon
    name: str
    tags: Dict[str, str]

    @classmethod
    def name_from_tags(cls, tags: Dict[str, str]):
        if 'name' in tags:
            return tags['name']
        if tags.get('landuse') == 'conservation':
            if tags.get('ownership') == 'municipal' and 'owner' in tags:
                return f'{tags["owner"]} Conservation Land'
            else:
                return 'Conservation Land'

        if tags.get('ownership') == 'municipal' and tags.get('owner') is not None:
            extra = ''
            if tags.get('leisure') == 'nature_reserve':
                extra = 'Nature Preserve'
            elif tags.get('boundary') == 'protected_area':
                extra = 'Protected Area'
            return f'{tags["owner"]} {extra}'
        elif len(tags) > 1:
            pass
            # print('Unable to get a name: ', tags)
        return 'Unnamed park'


def tags_to_dict(tags):
    return {t.k: t.v for t in tags}


class OsmiumTrailLoader(o.SimpleHandler):
    def __init__(self, location_filter: Optional[LocationFilter] = None):
        super(OsmiumTrailLoader, self).__init__()
        self.trails: Dict[int, Trail] = {}
        self.non_trail_nodes: Dict[int, str] = {}
        self.trail_nodes: Dict[int, Node] = {}
        self.location_filter = location_filter
        self.areas: Dict[int, Park] = {}

    def area(self, area):
        if area.tags.get('leisure') in PARKS or area.tags.get("boundary") in PARKISH_BOUNDARIES:
            # print('name :', area.tags.get('name'))
            # print(area.num_rings())
            border = MultiPolygon([Polygon([Point(n.lon, n.lat) for n in ring]) for ring in area.outer_rings()])
            if border is not None:
                tag_map = tags_to_dict(area.tags)
                self.areas[area.id] = Park(border, Park.name_from_tags(tag_map), tag_map)

    def way(self, w):
        if drivable(w):
            node_ids: Dict[int, str] = {n.ref: w.tags.get("name", "No name") for n in w.nodes}
            self.non_trail_nodes.update(node_ids)
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
                    if w.id in self.trails:
                        raise Exception('duplicate id!')
                    self.trails[w.id] = Trail.from_way(w)
                    for n in self.trails[w.id].nodes:
                        self.trail_nodes[n.id] = n
                except o.InvalidLocationError:
                    # A location error might occur if the osm file is an extract
                    # where nodes of ways near the boundary are missing.
                    print("WARNING: way %d incomplete. Ignoring." % w.id)


MIN_QUALITY = 0.7


class TrailheadMeta(NamedTuple):
    num_loops: int
    loop_diversity: float
    loop_quality: float
    longest_loop: float
    shortest_loop: float
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


class NetworkResult(NamedTuple):
    trail_network: TrailNetwork
    loops: Dict[Trailhead, TrailheadResult]

    def total_loops(self):
        return sum([len(l.loops) for l in self.loops.values()])


def worth_keeping(loop: Subpath):
    if loop.length_m < SHORTEST_LOOP.m:
        return False
    if loop.is_pure_out_and_back():
        return True
    else:
        return loop.quality() > MIN_QUALITY and loop.num_spurs() < 1


def meta(
        trail_network: TrailNetwork, loops: List[Subpath], time: float
) -> TrailheadMeta:
    num_loops = len(loops)
    if num_loops == 0:
        loop_quality = 0.
        loop_diversity = 0.
        longest_loop = 0.
        shortest_loop = 0.
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
    timeout_s: int = 10
    stop_searching_cutoff: Distance = Distance(mi=8)


DefaultQualitySettings = QualitySettings(repeat_node_weight=1)

DefaultIngestSettings = IngestSettings(
    max_concurrent=1000,
    max_distance=Distance(km=50),
    max_segments=50,
    quality_settings=DefaultQualitySettings,
)


def trail_length_km(trail):
    try:
        return trail.length_m() / 1000
    except:
        print('error?')
        return 1


class OSMIngestor:
    def __init__(self, ingest_settings: Optional[IngestSettings] = None, parallelism: int = 4) -> None:
        if ingest_settings is None:
            ingest_settings = DefaultIngestSettings
        self.ingest_settings = ingest_settings
        self.trails: Dict[int, Trail] = {}
        self.parks: Dict[int, Park] = {}
        self.non_trail_nodes: Dict[int, str] = {}
        self.global_graph = nx.MultiGraph()
        self.nodes: Dict[int, Node] = {}
        self.trailnetwork_results: Dict[
            TrailNetwork, Dict[Trailhead, TrailheadResult]
        ] = {}
        self.pool = Pool(parallelism)

    def load_osm(self, filename: Path, extra_links: List[Tuple[int, int]] = None, no_road_crossings=True):
        if extra_links is None:
            extra_links = []
        osm_loader = OsmiumTrailLoader(self.ingest_settings.location_filter)
        print(f"Loading trails from {filename}")
        osm_loader.apply_file(str(filename), locations=True, idx='flex_mem')
        print(f"Loaded from {filename}")
        trails = osm_loader.trails
        for node_ids in extra_links:
            if not all(n in osm_loader.trail_nodes for n in node_ids):
                continue
            trails[sum(node_ids)] = Trail(
                nodes=[osm_loader.trail_nodes[n] for n in node_ids],
                way_id=f'extra-{node_ids[0]}-{node_ids[1]}',
                name='Manually added trail',
                manual=True
            )
        self.parks = osm_loader.areas
        print(f"Importing {len(trails)} trails and {len(osm_loader.areas)} areas")
        self.trails.update(trails)
        self.non_trail_nodes.update(osm_loader.non_trail_nodes)
        self.add_trails_to_graph(trails.values(), no_road_crossings=no_road_crossings,
                                 dont_touch=set([e for link in extra_links for e in link]))

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

    def add_trails_to_graph(self, new_trails, dont_touch: Set[int], no_road_crossings=False):
        non_trail_nodes = set(self.non_trail_nodes.keys())
        segmented_trails = segment_trails(new_trails, non_trail_nodes)
        if no_road_crossings:
            disconnect_road_crossings(segmented_trails, non_trail_nodes, dont_touch)

        G = self.global_graph
        special = []
        for trail in segmented_trails:
            special += [node for node in trail.nodes if 4583062189 == node.osm_id]
            G.add_node(trail.nodes[0]),
            G.add_node(trail.nodes[-1])
        print('\n  '.join([str(s) for s in special]))
        assert len(set(special)) == len(special)

        ids = set()
        for trail in segmented_trails:
            if no_road_crossings and all(
                    node.osm_id in self.non_trail_nodes for node in (trail.nodes[0], trail.nodes[-1])):
                continue
            ids.add(trail.id)
            if trail.nodes[0] in special:
                print(trail.nodes[0], trail.nodes[-1])
            if trail.nodes[-1] in special:
                print(trail.nodes[0], trail.nodes[-1])
            G.add_edge(
                trail.nodes[0],
                trail.nodes[-1],
                weight=trail.length_m() / 1000,
                name=trail.name,
                trail=trail,
            )

    def trail_networks(self, already_processed: Set[str] = None):
        G = self.global_graph
        for c in nx.connected_components(G):
            # intersecting = [n for n in c if n.osm_id == 3268105766]
            # if intersecting:
            #    import pdb; pdb.set_trace()
            # print('intersection: ', len(intersecting), intersecting)
            digest = hashlib.sha256(''.join(sorted(str(n) for n in c)).encode('utf-8')).hexdigest()
            if already_processed is not None and digest in already_processed:
                continue
            if len(c) < 3:
                continue
            subgraph = G.subgraph(c)
            # ignore parks less than 1km long
            if subgraph.size(weight='weight') < 1:
                continue
            subgraph = subgraph.copy()
            network_border = MultiPoint([Point(x=n.lon, y=n.lat) for n in c]).convex_hull
            network_area = network_border.area
            if network_area == 0:
                print('Warning: network with 0 area, ignoring')
                continue
            name = None
            if network_border is not None:
                (best_park, best_overlap) = None, 0
                for park in self.parks.values():
                    if not park.border.intersects(network_border):
                        continue
                    try:
                        p_overlap = network_border.intersection(park.border).area / network_area
                        if p_overlap > best_overlap:
                            best_park = park
                            best_overlap = p_overlap
                    except GEOSException as err:
                        print(f'Error {err} for {park.name}')

                if best_overlap > 0:
                    name = best_park.name
            network = TrailNetwork(
                subgraph,
                self.non_trail_nodes,
                self.ingest_settings.trailhead_distance_threshold,
                digest=digest,
                name=name
            )
            yield network

    def trailheads(self) -> Iterator[Trailhead]:
        for network in self.trail_networks():
            for trailhead in network.trailheads:
                yield trailhead


def build_derived_id(trail: Trail, node_id: int):
    # important to potentially used a derived id here since a trail might
    # be split crossing a road
    return NodeId(f"{node_id}-{trail.id}-road-extra")


def disconnect_road_crossings(trails: List[Trail], non_trail_nodes: Set[int], dont_touch: Set[int]):
    for trail in trails:
        for index in (0, -1):
            node = trail.nodes[index]
            if node.osm_id in dont_touch:
                continue
            if node.osm_id in non_trail_nodes:
                trail.nodes[index] = node._replace(derived_id=build_derived_id(trail, node.osm_id))


def segment_trails(trails: List[Trail], non_trail_nodes: Set[int]) -> List[Trail]:
    """Returns a new list of trails where all intersections are at the start or end"""
    graph = InverseGraph()
    for trail in trails:
        graph.add_trail(trail)

    flat_trails: List[Trail] = []
    for trail in trails:
        split_idxs = []
        for (i, node) in enumerate(trail.nodes[1:-1], 1):
            if len(graph.node_trail_map[node.osm_id]) > 1 or node.osm_id in non_trail_nodes:
                split_idxs.append(i)

        if split_idxs:
            flat_trails += trail.split_at(split_idxs)
        else:
            flat_trails.append(trail)
    # verify_identical_nodes(trails, flat_trails)
    return flat_trails


SHORTEST_LOOP = Distance(km=3)


def problematic_network(network):
    total_distance = network.total_length()
    subgraph = network.graph
    num_edges = len(subgraph.edges)
    if (total_distance.km / num_edges) < 0.1:
        return True
    else:
        return False

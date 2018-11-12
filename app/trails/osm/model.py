import copy
import random
import time
from collections import defaultdict, Counter
from functools import reduce
from typing import NamedTuple, List, Iterator, Dict, Optional

import geopy.distance
import gpxpy
import gpxpy.gpx
import srtm
from measurement.measures import Distance
from networkx.classes.graphviews import SubGraph

from osm.util import memoize, window, verify_identical_nodes

elevation = srtm.get_data()


class Node(NamedTuple):
    id: int
    lat: float
    lon: float

    def elevation(self):
        try:
            return elevation.get_elevation(self.lat, self.lon)
        except Exception as e:
            time.sleep(1)
            print('Failed to get elevation. Retrying in 1s', e)
            return self.elevation()

    def distance(self, other: "Node") -> Distance:
        return Distance(
            m=geopy.distance.great_circle(
                (self.lat, self.lon), (other.lat, other.lon)
            ).m
        )


class ElevationChange(NamedTuple):
    gain: float
    loss: float

    @classmethod
    def to_elevated_gps(cls, nodes: Iterator[Node]):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        # Create points:
        for node in nodes:
            gpx_segment.points.append(
                gpxpy.gpx.GPXTrackPoint(latitude=node.lat, longitude=node.lon)
            )

        try:
            elevation.add_elevations(gpx, smooth=True)
            return gpx_segment
        except Exception as ex:
            time.sleep(1)
            print('error while adding elevations', ex)
            return ElevationChange.to_elevated_gps(nodes)

    @classmethod
    def elevations(cls, nodes: Iterator[Node]):
        gpx_segment = cls.to_elevated_gps(nodes)
        return [p.elevation for p in gpx_segment.points]

    @classmethod
    def from_nodes(cls, nodes: Iterator[Node]):
        gpx_segment = cls.to_elevated_gps(nodes)
        (gain, loss) = gpx_segment.get_uphill_downhill()
        return cls(gain, loss)


trail_length_cache = {}


class Trail:
    def __init__(self, nodes, way_id, name: Optional[str], derived_id=None):
        self.nodes = nodes
        self.way_id: str = way_id
        self.id = derived_id or way_id
        self.name = name

    @memoize
    def length(self):
        dists = [
            geopy.distance.great_circle((a.lat, a.lon), (b.lat, b.lon)).m
            for (a, b) in window(self.nodes)
        ]
        return Distance(m=sum(dists))

    @memoize
    def length_m(self):
        dists = [
            geopy.distance.great_circle((a.lat, a.lon), (b.lat, b.lon)).m
            for (a, b) in window(self.nodes)
        ]
        return sum(dists)

    @classmethod
    def from_way(cls, way):
        nodes = [Node(node.ref, node.lat, node.lon) for node in way.nodes]
        id = str(way.id)

        if way.tags.get("name"):
            name = way.tags["name"]
        else:
            name = None
        return cls(nodes=nodes, way_id=id, name=name)

    def split_at(self, idxs):
        start_idx = 0
        result = []
        for seg_num, idx in enumerate(idxs):
            new_nodes = self.nodes[start_idx: idx + 1]
            new_id = f"{self.way_id}-{seg_num}/{len(idxs)}"
            result.append(
                Trail(
                    nodes=new_nodes,
                    way_id=self.way_id,
                    derived_id=new_id,
                    name=self.name,
                )
            )
            start_idx = idx

        final_nodes = self.nodes[start_idx:]
        if not final_nodes:
            assert "Unexpected empty final nodes"
        result.append(
            Trail(
                nodes=final_nodes,
                way_id=self.way_id,
                derived_id=f"{self.way_id}-{len(idxs)}/{len(idxs)}",
                name=self.name,
            )
        )
        verify_identical_nodes([self], result)
        return result

    @memoize
    def elevation(self):
        return ElevationChange.from_nodes(self.nodes)

    @memoize
    def reverse(self):
        return Trail(
            nodes=list(reversed(self.nodes)),
            way_id=self.way_id,
            derived_id=self.id,
            name=self.name,
        )

    def draw(self, gmap, color=None):
        lats = [n.lat for n in self.nodes]
        lons = [n.lon for n in self.nodes]
        color = color or random.choice(list(gmap.html_color_codes.keys()))
        gmap.plot(lats, lons, color, edge_width=2)


class Trailhead(NamedTuple):
    node: Node
    name: str


class TrailNetwork:
    def __init__(
            self,
            subgraph: SubGraph,
            nontrail_nodeset: Dict[int, str],
            distance_threshold: Distance,
    ) -> None:
        self.graph = subgraph
        max_trailheads = int(self.total_length().km) // 2
        raw_trailheads = [
            Trailhead(node, nontrail_nodeset[node.id])
            for node in subgraph.nodes
            if node.id in nontrail_nodeset
        ]
        self.num_raw = len(raw_trailheads)
        raw_trailheads = self.cluster_trailheads(raw_trailheads, distance_threshold)
        self.num_clustered = len(raw_trailheads)
        self.trailheads: List[Trailhead] = raw_trailheads[:max_trailheads]

    def cluster_trailheads(self, trailheads, distance_threshold: Distance):
        if not trailheads:
            return []
        trailheads_to_keep = [trailheads[0]]
        for trailhead in trailheads[1:]:
            closest = min(
                [
                    trailhead.node.distance(existing.node)
                    for existing in trailheads_to_keep
                ]
            )
            if closest > distance_threshold:
                trailheads_to_keep.append(trailhead)
        return trailheads_to_keep

    @memoize
    def total_length_km(self):
        total_length = 0
        for edge in self.graph.edges:
            total_length += self.graph[edge[0]][edge[1]]["weight"]
        return total_length

    @memoize
    def total_length(self) -> Distance:
        return Distance(km=self.total_length_km())

    def unique_id(self):
        way_ids = {trail.way_id for trail in self.trail_segments()}
        return ",".join(sorted(way_ids))

    def __eq__(self, other):
        return isinstance(other, TrailNetwork) and self.unique_id() == other.unique_id()

    def __hash__(self):
        return self.unique_id().__hash__()

    """
    def bounding_box(self):
        top_left = None
        bottom_right = None
        for trail in self.trail_segments():
            for node in trail.nodes():
                if top_left is None:
                    top_left = node
                if bottom_right is None:
                    bottom_right = node
    """

    @memoize
    def trail_names(self):
        names = set()
        for edge in self.graph.edges:
            names.add(self.graph[edge[0]][edge[1]]["name"])
        return names

    def trail_segments(self) -> Iterator[Trail]:
        for edge in self.graph.edges:
            yield self.graph[edge[0]][edge[1]]["trail"]

    def __repr__(self):
        return f"[trailheads={len(self.trailheads)}][total_length={self.total_length().km}][uid={self.unique_id()[:100]}]"


def filt_neg(d):
    return {k: v for k, v in d.items() if v > 0}


class Subpath:
    def __init__(
            self,
            segments: List[Trail],
            length_m: int,
            unique_length_m: int,
            segment_dist: Optional[Counter] = None,
    ) -> None:
        self.start_node = segments[0].nodes[0]
        self.trail_segments = segments
        self.segment_dist = segment_dist or Counter()
        if segment_dist is None:
            for s in self.trail_segments:
                self.segment_dist.update({s.id: s.length_m()})

        self.length_m = length_m
        self.unique_length_m = unique_length_m

        assert self.segment_dist.keys() == set([s.id for s in self.trail_segments])

    def record_node(self, node: Node, tracker):
        tracker.update({node.id})

    def compute_intersections(self):
        res = defaultdict(set)
        for segment in self.trail_segments:
            res[segment.nodes[0].id].add(segment.id)
            res[segment.nodes[-1].id].add(segment.id)
        del res[self.trail_segments[0].nodes[0].id]
        return res

    def name(self):
        trail_names = []
        for segment in self.trail_segments:
            if (
                    segment.name is not None
                    and self.segment_dist[segment.id] > self.length_m / 3
            ):
                if segment.name not in trail_names:
                    trail_names.append(segment.name)

        return "-".join(trail_names)

    # TESTS ONLY
    @classmethod
    def from_segments(cls, segments: List[Trail]):
        length = sum([segment.length_m() for segment in segments])
        # TODO: wrong
        return Subpath(segments, length, length)

    def similarity(self, other: "Subpath"):
        assert self.segment_dist.keys() == set([s.id for s in self.trail_segments])
        unique_paths = copy.deepcopy(self.segment_dist)  # Counter()
        # unique_paths += self.segment_dist
        unique_paths.subtract(other.segment_dist)

        unique_distance = sum([abs(v) for v in unique_paths.values()])

        total_distance = self.length_m + other.length_m
        return 1 - unique_distance / total_distance

    def is_pure_out_and_back(self):
        ts_ids = [ts.id for ts in self.trail_segments]
        return ts_ids == ts_ids[::-1] and self.quality() > 0.49

    @memoize
    def quality(self, repeat_weight=1):

        if self.length_m == 0:
            return 1

        repeat_quality = self.unique_length_m / self.length_m
        assert repeat_weight <= 1

        spur_quality = self.num_spurs() * -0.1

        graph_complexity = sum(
            [-0.1 * (len(v) - 2) for v in self.compute_intersections().values() if len(v) > 2]
        )
        if graph_complexity < 0:
            graph_complexity += 0.3
            graph_complexity = min(0, graph_complexity)

        q = repeat_quality * repeat_weight + spur_quality + graph_complexity
        assert q <= 1
        return max(q, 0)

    @classmethod
    def from_startnode(cls, starting_node: Node):
        trail_segments = [
            Trail(
                way_id="fakeroot", name="fakeroot", nodes=[starting_node, starting_node]
            )
        ]
        return cls(trail_segments, 0, 0)

    @memoize
    def num_spurs(self):
        n = 0
        for (t1, t2) in window(self.trail_segments):
            if t1.id == t2.id:
                n += 1
        return n

    def add_node(self, trail_segment: Trail, mutate=False) -> "Subpath":
        current_final = self.last_node()
        if trail_segment.nodes[0] == current_final:
            new_segment = trail_segment
        else:
            new_segment = trail_segment.reverse()

        if new_segment.id not in self.segment_dist:
            unique_length = new_segment.length_m()
        else:
            unique_length = 0

        if mutate:
            self.trail_segments.append(new_segment)
            self.segment_dist.update({trail_segment.id: trail_segment.length_m()})
            self.unique_length_m += unique_length
            self.length_m += new_segment.length_m()
            return self
        else:
            new_segment_dist = copy.deepcopy(self.segment_dist)
            new_segment_dist.update({trail_segment.id: trail_segment.length_m()})

            return Subpath(
                list(self.trail_segments) + [new_segment],
                length_m=self.length_m + new_segment.length_m(),
                unique_length_m=self.unique_length_m + unique_length,
                segment_dist=new_segment_dist,
            )

    def nodes(self) -> Iterator[Node]:
        for seg in self.trail_segments:
            for node in seg.nodes:
                yield node

    def is_complete(self):
        return self.trail_segments[0].nodes[0] == self.last_node()

    @memoize
    def elevation_change(self) -> ElevationChange:
        return ElevationChange.from_nodes(self.nodes())

    def first_node(self):
        return self.trail_segments[0].nodes[0]

    def last_node(self):
        return self.trail_segments[-1].nodes[-1]

    def __repr__(self):
        names = [seg.name or "noname" for seg in self.trail_segments]
        if self.is_complete():
            names.append("fakeroot")
        return f'{self.length_m / 1000}: {"<->".join(names)}'

    def draw(self, gmap):
        for trail in self.trail_segments:
            trail.draw(gmap)


class InverseGraph:
    def __init__(self):
        self.node_trail_map = defaultdict(list)
        self.trails = {}

    def add_trail(self, trail: Trail):
        self.trails[trail.id] = trail
        for node in trail.nodes:
            self.node_trail_map[node.id].append(trail.id)

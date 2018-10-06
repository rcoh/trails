import random
from collections import defaultdict, Counter
from functools import reduce
from typing import NamedTuple, List, Set, Iterator, Dict

import geopy.distance
import srtm
from networkx.classes.graphviews import SubGraph
import gpxpy
import gpxpy.gpx

from osm.util import memoize, window, verify_identical_nodes

elevation = srtm.get_data()


class Node(NamedTuple):
    id: int
    lat: float
    lon: float

    def elevation(self):
        return elevation.get_elevation(self.lat, self.lon)

    def distance(self, other: 'Node'):
        return geopy.distance.great_circle((self.lat, self.lon), (other.lat, other.lon))


class ElevationChange(NamedTuple):
    gain: float
    loss: float

    @classmethod
    def from_nodes(cls, nodes: Iterator[Node]):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        # Create points:
        for node in nodes:
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=node.lat, longitude=node.lon))

        elevation.add_elevations(gpx, smooth=True)
        (gain, loss) = gpx_segment.get_uphill_downhill()
        return cls(gain, loss)


trail_length_cache = {}


class Trail:
    def __init__(self, nodes, way_id, name, derived_id=None, reversed=False):
        self.nodes = nodes
        self.way_id: str = way_id
        self.id = derived_id or way_id
        self.name = name
        self.reversed = reversed

    @memoize
    def length(self):
        dists = [
            geopy.distance.great_circle((a.lat, a.lon), (b.lat, b.lon))
            for (a, b) in window(self.nodes)
        ]
        return reduce(lambda x, y: x + y, dists)

    @classmethod
    def from_way(cls, way):
        nodes = []
        id = str(way.id)
        for node in way.nodes:
            n = Node(node.ref, node.lat, node.lon)
            nodes.append(n)

        if way.tags.get("name"):
            name = way.tags["name"]
        else:
            name = "unamed"
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
    def __init__(self, subgraph: SubGraph, nontrail_nodeset: Dict[int, str]) -> None:
        self.graph = subgraph
        self.trailheads: List[Trailhead] = [
            Trailhead(node, nontrail_nodeset[node.id])
            for node in subgraph.nodes
            if node.id in nontrail_nodeset
        ]

    @memoize
    def total_length_km(self):
        total_length = 0
        for edge in self.graph.edges:
            total_length += self.graph[edge[0]][edge[1]]["weight"]
        return total_length

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


def filt_neg(d):
    return {k: v for k, v in d.items() if v > 0}


class Subpath:
    def __init__(self, segments: List[Trail], length_km, unique_length) -> None:
        self.start_node = segments[0].nodes[0]
        self.trail_segments = segments
        self.segment_dist = Counter()
        for s in self.trail_segments:
            self.segment_dist.update({s.id: s.length().km})

        self.length_km = length_km
        self.unique_length = unique_length

        assert self.segment_dist.keys() == set([s.id for s in self.trail_segments])

    @classmethod
    def from_segments(cls, segments: List[Trail]):
        length_km = sum([segment.length().km for segment in segments])
        # TODO: wrong
        return Subpath(segments, length_km, length_km)

    def similarity(self, other: "Subpath"):
        assert self.segment_dist.keys() == set([s.id for s in self.trail_segments])
        unique_paths = Counter()
        unique_paths += self.segment_dist
        unique_paths.subtract(other.segment_dist)

        unique_distance = sum([abs(v) for v in unique_paths.values()])

        total_distance = self.length_km + other.length_km
        return 1 - unique_distance / total_distance

    @memoize
    def quality(self, repeat_weight=1):
        if self.length_km == 0:
            return 1
        repeat_quality = self.unique_length / self.length_km
        return repeat_quality * repeat_weight

    @classmethod
    def from_startnode(cls, starting_node: Node):
        trail_segments = [
            Trail(
                way_id="fakeroot", name="fakeroot", nodes=[starting_node, starting_node]
            )
        ]
        return cls(trail_segments, 0, 0)

    def add_node(self, trail_segment: Trail):
        current_final = self.last_node()
        if trail_segment.nodes[0] == current_final:
            new_segment = trail_segment
        else:
            new_segment = trail_segment.reverse()

        if new_segment.id not in self.segment_dist:
            unique_length = new_segment.length().km
        else:
            unique_length = 0

        return Subpath(list(self.trail_segments) + [new_segment], length_km=self.length_km + new_segment.length().km,
                       unique_length=self.unique_length + unique_length)

    def nodes(self) -> Iterator[Node]:
        for seg in self.trail_segments:
            for node in seg.nodes:
                yield node

    def is_complete(self):
        return self.trail_segments[0].nodes[0] == self.last_node()

    @memoize
    def length_km(self):
        return sum([t.length().km for t in self.trail_segments])

    @memoize
    def elevation_change(self) -> ElevationChange:
        return ElevationChange.from_nodes(self.nodes())

    def last_node(self):
        return self.trail_segments[-1].nodes[-1]

    def __repr__(self):
        names = [seg.name for seg in self.trail_segments]
        if self.is_complete():
            names.append("fakeroot")
        return f'{self.length_km}: {"<->".join(names)}'

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

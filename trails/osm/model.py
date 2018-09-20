import random
from collections import defaultdict
from functools import reduce
from typing import NamedTuple, List, Set, Iterator, Dict

import geopy.distance
import srtm
from networkx.classes.graphviews import SubGraph

from osm.util import memoize, window, verify_identical_nodes


class Node(NamedTuple):
    id: int
    lat: float
    lon: float



elevation = srtm.get_data()


class ElevationChange(NamedTuple):
    gain: float
    loss: float

    @classmethod
    def from_nodes(cls, nodes: Iterator[Node]):
        gain = 0
        loss = 0
        for n1, n2 in window(nodes):
            e1 = elevation.get_elevation(n1.lat, n1.lon)
            e2 = elevation.get_elevation(n2.lat, n2.lon)
            if e2 > e1:
                gain += e2 - e1
            else:
                loss += e1 - e2
        return cls(gain, loss)


class Trail:
    def __init__(self, nodes, way_id, name, derived_id=None, reversed=False):
        self.nodes = nodes
        self.way_id: str = way_id
        self.id = derived_id or way_id
        self.name = name
        self.reversed = reversed

    @memoize
    def length(self):
        dists = [geopy.distance.great_circle((a.lat, a.lon), (b.lat, b.lon)) for (a, b) in window(self.nodes)]
        return reduce(lambda x, y: x + y, dists)

    @classmethod
    def from_way(cls, way):
        nodes = []
        id = str(way.id)
        for node in way.nodes:
            n = Node(node.ref, node.lat, node.lon)
            nodes.append(n)

        if way.tags.get('name'):
            name = way.tags['name']
        else:
            name = 'unamed'
        return cls(nodes=nodes, way_id=id, name=name)

    def split_at(self, idxs):
        start_idx = 0
        result = []
        for seg_num, idx in enumerate(idxs):
            new_nodes = self.nodes[start_idx:idx + 1]
            new_id = f'{self.way_id}-{seg_num}/{len(idxs)}'
            result.append(Trail(nodes=new_nodes, way_id=self.way_id, derived_id=new_id, name=self.name))
            start_idx = idx

        final_nodes = self.nodes[start_idx:]
        if not final_nodes:
            assert 'Unexpected empty final nodes'
        result.append(Trail(nodes=final_nodes, way_id=self.way_id, derived_id=f'{self.way_id}-{len(idxs)}/{len(idxs)}',
                            name=self.name))
        verify_identical_nodes([self], result)
        return result

    @memoize
    def elevation(self):
        return ElevationChange.from_nodes(self.nodes)

    @memoize
    def reverse(self):
        return Trail(nodes=list(reversed(self.nodes)), way_id=self.way_id, derived_id=f'{self.id}-rev', name=self.name)

    def draw(self, gmap, color=None):
        lats = [n.lat for n in self.nodes]
        lons = [n.lon for n in self.nodes]
        color = color or random.choice(list(gmap.html_color_codes.keys()))
        gmap.plot(lats, lons, color, edge_width=5)


class Trailhead(NamedTuple):
    node: Node
    name: str


class TrailNetwork:
    def __init__(self, subgraph: SubGraph, nontrail_nodeset: Dict[int, str]):
        self.graph = subgraph
        self.trailheads: List[Trailhead] = [Trailhead(node, nontrail_nodeset[node.id]) for node in subgraph.nodes if
                                            node.id in nontrail_nodeset]

    @memoize
    def total_length_km(self):
        total_length = 0
        for edge in self.graph.edges:
            total_length += self.graph[edge[0]][edge[1]]['weight']
        return total_length

    def unique_id(self):
        way_ids = {trail.way_id for trail in self.trail_segments()}
        return ','.join(sorted(way_ids))

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
            names.add(self.graph[edge[0]][edge[1]]['name'])
        return names

    def trail_segments(self) -> Iterator[Trail]:
        for edge in self.graph.edges:
            yield self.graph[edge[0]][edge[1]]['trail']

    def find_loops(self, trailhead: Node, max_segments=50, max_distance_km=55, max_concurrent=100):
        random.seed(735)
        complete_paths = []
        active_paths = [Subpath.from_startnode(trailhead)]
        while active_paths:
            filtered_paths = []
            for path in active_paths:
                if path.length_km() < max_distance_km and len(path.trail_segments) < max_segments:
                    filtered_paths.append(path)
            active_paths = filtered_paths
            final_paths = []
            random.shuffle(active_paths)
            active_paths = active_paths[:max_concurrent]
            for path in active_paths:
                options = list(dict(self.graph[path.last_node()]).items())
                random.shuffle(options)
                for next_node, next_trail in options:
                    if next_trail['trail'].id == path.trail_segments[-1].id:
                        continue
                    new_path = path.fork()
                    is_loop = new_path.add_node(next_trail['trail'])
                    if is_loop:
                        yield new_path
                    final_paths.append(new_path)
            active_paths = final_paths
        return complete_paths


class Subpath:

    @classmethod
    def from_startnode(cls, starting_node: Node):
        trail_segments = [Trail(way_id='fakeroot', name='fakeroot', nodes=[starting_node, starting_node])]
        return cls(trail_segments)

    def __init__(self, segments: List[Trail]):
        self.start_node = segments[0].nodes[0]
        self.trail_segments = segments

    def add_node(self, trail_segment: Trail):
        current_final = self.last_node()
        if trail_segment.nodes[0] == current_final:
            self.trail_segments.append(trail_segment)
        else:
            self.trail_segments.append(trail_segment.reverse())

        return self.is_complete()

    def nodes(self):
        for seg in self.trail_segments:
            for node in seg.nodes:
                yield node

    def is_complete(self):
        return self.trail_segments[0].nodes[0] == self.last_node()

    def fork(self):
        return Subpath(list(self.trail_segments))

    @memoize
    def length_km(self):
        return sum([t.length().km for t in self.trail_segments])

    @memoize
    def elevation_change(self):
        return ElevationChange.from_nodes(self.nodes())

    def last_node(self):
        return self.trail_segments[-1].nodes[-1]

    def __repr__(self):
        names = [seg.name for seg in self.trail_segments]
        if self.is_complete():
            names.append('fakeroot')
        return f'{self.length_km()}: {"<->".join(names)}'

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

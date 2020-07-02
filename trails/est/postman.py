import csv
from io import BytesIO
from tempfile import NamedTemporaryFile

from django.contrib.gis.geos import Point, LineString
from measurement.measures import Distance
from networkx import read_gpickle
from postman_problems import solver
from postman_problems.stats import calculate_postman_solution_stats

from est.models import TrailNetwork, Circuit
from osm.model import segments_for_graph


def circuit_to_line_string(circuit, edge_map):
    line_string = []
    for i, segment in enumerate(circuit):
        start, end, _, meta = segment
        nodes = edge_map[meta['id']]
        if int(end) == nodes[0].id:
            nodes = reversed(nodes)
        line_string += [Point(x=node.lon, y=node.lat, z=0) for node in nodes]
    return LineString(line_string)


def circuits(network: TrailNetwork):
    existing_circuits = Circuit.objects.filter(network=network)
    if existing_circuits.exists():
        return existing_circuits.first()
    else:
        graph = read_gpickle(BytesIO(network.graph.tobytes()))
        with NamedTemporaryFile(suffix='.csv', mode='w') as f:
            writer = csv.DictWriter(f, fieldnames=['start', 'end', 'id', 'distance'])
            writer.writeheader()
            edge_map = {}
            for segment in segments_for_graph(graph):
                writer.writerow(dict(start=segment.nodes[0].id, end=segment.nodes[-1].id, id=segment.id,
                                     distance=segment.length_m()))
                edge_map[segment.id] = segment.nodes
            f.flush()
            circuit, _ = solver.cpp(f.name)
            stats = calculate_postman_solution_stats(circuit)
            walked_twice = Distance(m=stats['distance_doublebacked'])
            walked_total = Distance(m=stats['distance_walked_required'])

            line_string = circuit_to_line_string(circuit, edge_map)
            return Circuit.objects.create(
                route=line_string,
                total_length=walked_total,
                network=network
            )

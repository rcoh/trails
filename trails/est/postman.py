import csv
from io import BytesIO
from tempfile import NamedTemporaryFile

from django.contrib.gis.geos import Point, LineString
from measurement.measures import Distance
from networkx import read_gpickle
from postman_problems import solver
from postman_problems.stats import calculate_postman_solution_stats

from est.models import TrailNetwork, Circuit, Complete, Error, InProgress
from osm.model import segments_for_graph
from trails.celery import app


def circuit_to_line_string(circuit, edge_map):
    line_string = []
    for i, segment in enumerate(circuit):
        start, end, _, meta = segment
        nodes = edge_map[meta['id']]
        if end == nodes[0].derived_id:
            nodes = reversed(nodes)
        line_string += [Point(x=node.lon, y=node.lat, z=0) for node in nodes]
    return LineString(line_string)


def find_or_compute_circuit(network: TrailNetwork):
    existing_circuits = Circuit.objects.filter(network=network)
    if existing_circuits.exists():
        circuit = existing_circuits.first()
        if circuit.status == Complete:
            return existing_circuits.first()
        else:
            status = create_circuit.delay(network.id, circuit.id)
            print(status)
            return circuit
    else:
        circuit = Circuit.objects.create(
            network=network,
            status=1
        )
        status = create_circuit.delay(network.id, circuit.id)
        print(status)
        return circuit


@app.task(bind=True)
def create_circuit(self, network_id: str, circuit_id: str):
    network = TrailNetwork.objects.get(id=network_id)
    circuit = Circuit.objects.get(id=circuit_id)
    circuit.status = InProgress
    circuit.error = ""
    circuit.save()
    try:
        graph = read_gpickle(BytesIO(network.graph.tobytes()))
        with NamedTemporaryFile(suffix='.csv', mode='w') as f:
            writer = csv.DictWriter(f, fieldnames=['start', 'end', 'id', 'distance'])
            writer.writeheader()
            edge_map = {}
            for segment in segments_for_graph(graph):
                writer.writerow(dict(start=segment.nodes[0].derived_id, end=segment.nodes[-1].derived_id, id=segment.id,
                                     distance=segment.length_m()))
                edge_map[segment.id] = segment.nodes
            f.flush()
            circuit_nodes, _ = solver.cpp(f.name)
            stats = calculate_postman_solution_stats(circuit_nodes)
            walked_twice = Distance(m=stats['distance_doublebacked'])
            walked_total = Distance(m=stats['distance_walked_required'])

            line_string = circuit_to_line_string(circuit_nodes, edge_map)
            circuit.route = line_string
            circuit.total_length = walked_total
            circuit.status = Complete
            circuit.error = ""
    except Exception as ex:
        circuit.status = Error
        circuit.error = ex
        raise
    finally:
        circuit.save()

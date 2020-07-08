from io import BytesIO
from multiprocessing import Pool

import djclick as click
from measurement.measures import Distance
from networkx import read_gpickle

from tqdm import tqdm

from est.models import TrailNetwork
from osm import util


def recalculate(network: TrailNetwork):
    graph = read_gpickle(BytesIO(network.graph.tobytes()))
    calculated_length = sum([w.length_m() / 1000 for _, _, w in graph.edges.data('trail')])
    network.total_length = Distance(m=calculated_length)
    network.save()


@click.command()
def recalculate_lengths():
    for network in tqdm(TrailNetwork.objects.all(), total=TrailNetwork.objects.count()):
        graph = read_gpickle(BytesIO(network.graph.tobytes()))
        calculated_length = sum([w.length_m() / 1000 for _, _, w in graph.edges.data('trail')])
        network.total_length = Distance(m=calculated_length)
        network.save()

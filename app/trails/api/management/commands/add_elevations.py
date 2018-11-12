import djclick as click
from tqdm import tqdm

from api.models import Route


@click.command()
def add_elevations():
    for route in tqdm(Route.objects.all(), total=Route.objects.count()):
        route.add_elevations()
        route.save()

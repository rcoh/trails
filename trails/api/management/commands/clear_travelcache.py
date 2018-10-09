import djclick as click

from api.models import TravelCache


@click.command()
def clear_travelcache():
    TravelCache.objects.all().delete()

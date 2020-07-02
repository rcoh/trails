import djclick as click
import requests
from django.core.serializers import serialize

import est.models as e


@click.command()
@click.argument('target', type=click.STRING, default="http://everysingletrail.com")
def export(target):
    most_recent_import = e.Import.objects.order_by('-created_at').first()
    click.confirm(f'Importing {most_recent_import.networks.count()} networks imported {most_recent_import.created_at}')
    networks = serialize('json', most_recent_import.networks.all())
    import_obj = serialize('json', [most_recent_import])
    resp = requests.post(f"{target}/api/import", json=dict(import_record=import_obj, networks=networks))
    print(resp.content)
    print(resp.json())

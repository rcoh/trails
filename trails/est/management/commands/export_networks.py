import djclick as click
from tqdm import tqdm
import requests
from django.core.serializers import serialize

from django.core.paginator import Paginator
import est.models as e


@click.command()
@click.argument('target', type=click.STRING, default="https://everysingletrail.com")
def export(target):
    imports = e.Import.objects.filter(complete=True, active=True).order_by('-updated_at')
    for most_recent_import in tqdm(imports):
        #if not click.confirm(
        #        f'Importing {most_recent_import.networks.count()} networks ({most_recent_import.name}) imported {most_recent_import.created_at}'):
        #    continue
        loaded = requests.get(f"{target}/api/import/{most_recent_import.id}/").json()
        # print(f'{len(loaded["ids"])} already loaded')
        if loaded["ids"]:
            tqdm.write(f"{len(loaded['ids'])} already loaded")
        #ids = [network.id for network in most_recent_import.networks]
        p = Paginator(most_recent_import.networks.exclude(id__in=loaded['ids']).order_by('id'), 32)
        for i in p.page_range:
            page = p.page(i)
            networks = serialize('json', page)
            import_obj = serialize('json', [most_recent_import])
            resp = requests.post(f"{target}/api/import", json=dict(import_record=import_obj, networks=networks))
            if not resp.ok:
                import pdb;
                pdb.set_trace()
    # print(resp.json())

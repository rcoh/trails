from multiprocessing.pool import Pool

import djclick as click
from tqdm import tqdm

from api.models import Route


def add_elevation(route):
    route = Route.objects.get(id=route.id)
    if route.elevation_gain == 0:
        print(f"{route.id} has no elevation data")
        return route.id
    if route.nodes[0][2] != 0:
        return (route.id, 1)
    try:
        if route.add_elevations():
            route.save()
            return (route.id, 1)
        else:
            print(f"failed {route.id}")
            return (route.id, 0)
    except Exception as ex:
        print(f"failed {route.id}")
        return (route.id, 0)


import gc


def queryset_iterator(queryset, chunksize=500):
    """''
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    """
    pk = 0
    last_pk = queryset.order_by("-pk")[0].pk
    queryset = queryset.order_by("pk")
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


@click.command()
@click.option("--parallelism", "-p", type=click.INT)
@click.option("--route-id", type=click.INT)
@click.option("--start-id", type=click.INT)
def add_elevations(parallelism, route_id, start_id):
    if route_id:
        print("result: ", add_elevation(Route.objects.get(id=route_id)))
        return

    p = Pool(parallelism)
    base_query = Route.objects.all()  # [:50]
    if start_id:
        base_query = base_query.filter(id__gt=start_id)

    all_routes = queryset_iterator(base_query.only("id"))
    piter = p.imap_unordered(add_elevation, all_routes, chunksize=100)
    total = 0
    iters = 0
    pbar = tqdm(piter, total=base_query.count())
    for (rid, n) in pbar:
        total += n
        iters += 1
        if iters % 1000 == 0:
            pbar.set_description(f"Success {int(total/iters*100)}% latest: {rid}")

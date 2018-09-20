import djclick as click
import gmplot

from api.models import Trailhead


@click.command()
def plot_trailheads():
    gmap = gmplot.GoogleMapPlotter(37.4684697, -122.2895862, 13)
    trailheads = Trailhead.objects.all()
    for trailhead in trailheads:
        gmap.marker(
            lat=trailhead.node.lat, lng=trailhead.node.lon, title=trailhead.node.osm_id
        )
        print(trailhead.node.osm_id)
    gmap.draw("out.html")

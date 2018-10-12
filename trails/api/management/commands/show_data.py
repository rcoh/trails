import djclick as click
from gmplot import gmplot

from api.models import Trailhead
from osm.loader import LocationFilter


@click.command()
@click.option("--center", type=click.STRING)
@click.option("--radius", type=click.INT)
@click.option("--output-file", type=click.STRING, default="out.html")
def draw_trails(center, radius, output_file):
    if center:
        lat, lon = center.split(",")
        if radius is None:
            click.secho("Radius must be specified with lat/lon", fg="red")
            exit(1)
        location_filter = LocationFilter(float(lat), float(lon), radius_km=radius)
    else:
        location_filter = None

    trailheads = Trailhead.objects.all()
    gmap = gmplot.GoogleMapPlotter(37.4684697, -122.2895862, 13)
    for trailhead in trailheads:
        print("drawing trailhead")
        trailhead.draw(gmap)

    gmap.draw(output_file)

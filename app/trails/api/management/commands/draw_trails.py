from typing import Optional

import djclick as click
from gmplot import gmplot

from osm.loader import LocationFilter, OsmiumTrailLoader


@click.command()
@click.option("file")
@click.option("--center", type=click.STRING)
@click.option("--radius", type=click.INT)
@click.option("--output-file", type=click.STRING, default="out.html")
def draw_trails(file: Optional[str], center, radius, output_file):
    if center:
        lat, lon = center.split(",")
        if radius is None:
            click.secho("Radius must be specified with lat/lon", fg="red")
            exit(1)
        location_filter: Optional[LocationFilter] = LocationFilter(
            float(lat), float(lon), radius_km=radius
        )
    else:
        location_filter: Optional[LocationFilter] = None
    trail_loader = OsmiumTrailLoader(location_filter)
    trail_loader.apply_file(file, locations=True)
    gmap = gmplot.GoogleMapPlotter(37.4684697, -122.2895862, 13)
    for _, trail in trail_loader.trails.items():
        trail.draw(gmap)

    gmap.draw(output_file)

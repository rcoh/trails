import itertools
from typing import NamedTuple

from tqdm import tqdm

from pyqtree import Index
import djclick as click
import geopy
import geopy.distance
import gpxpy.gpx
from django.contrib.gis.geos import MultiLineString, Point
from measurement.measures import Distance

from api.models import TrailNetwork


def sliding_window(iterable, n=2):
    iterables = itertools.tee(iterable, n)

    for iterable, num_skipped in zip(iterables, itertools.count()):
        for _ in range(num_skipped):
            next(iterable, None)

    return zip(*iterables)


def bbox(pt, tolerance: Distance):
    dist = geopy.distance.GreatCircleDistance(meters=tolerance.m)
    ul = dist.destination(pt, 360 - 45)
    br = dist.destination(pt, 90 + 45)
    return (ul.longitude, ul.latitude, br.longitude, br.latitude)


class TrailSegment(NamedTuple):
    p0: Point
    p1: Point

    def midpoint(self):
        return Point(x=(self.p0.x + self.p1.x) / 2, y=(self.p0.y + self.p1.y) / 2)

    def contains_point(self, lat, lon, tolerance: Distance) -> bool:
        return self.distance(self.midpoint(), lat, lon) < tolerance

    def distance(self, p1: Point, lat, lon) -> Distance:
        return Distance(
            m=geopy.distance.great_circle((p1.x, p1.y), (lon, lat)).m
        )

    def length(self):
        return Distance(
            m=geopy.distance.great_circle((self.p1.x, self.p1.y), (self.p0.x, self.p0.y)).m
        )


    def bbox(self, tolerance):
        return bbox(self.midpoint(), tolerance=tolerance)


@click.command()
@click.argument('gpx', type=click.Path(exists=True))
def find_coverage(gpx):
    with open(gpx) as f:
        file = gpxpy.parse(f)

    trails: MultiLineString = TrailNetwork.objects.all()[0].trails
    segs = []
    for trail in trails:
        for p0, p1 in sliding_window(trail, 2):
            segs.append(TrailSegment(Point(p0), Point(p1)))
    midpoints = [seg.midpoint() for seg in segs]
    tree = Index(bbox=(
    min(p.x for p in midpoints), min(p.y for p in midpoints), max(p.x for p in midpoints), max(p.y for p in midpoints)))
    for seg in segs:
        tree.insert(seg, seg.bbox(Distance(m=100)))
    pts = [point for track in file.tracks for segment in track.segments for point in segment.points]
    covered_segments = set()
    for pt in tqdm(pts):
        relevant_segments = tree.intersect(bbox(Point(x=pt.longitude, y=pt.latitude), tolerance=Distance(m=1)))
        new_segments = [s for s in relevant_segments if s.contains_point(pt.latitude, pt.longitude, Distance(m=50))]
        if not new_segments:
            tqdm.write(f'warning: no segments found for {pt}')
        covered_segments.update(new_segments)

    import operator
    from functools import reduce
    import pdb; pdb.set_trace()
    print(sum((s.length().m for s in covered_segments), start=Distance(m=0)))
    print(sum((s.length().m for s in segs), start=Distance(m=0)))


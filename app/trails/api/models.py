import pickle

import geopy.distance
import gpxpy.gpx
from django.contrib.gis.db.models.functions import Distance as GisDistance
from django.contrib.gis.geos import Point, LineString
from django.contrib.gis.measure import D
from django.contrib.gis.db import models
from django_measurement.models import MeasurementField
from measurement.measures import Distance

# Create your models here.
import osm.model


class TrailNetwork(models.Model):
    name = models.CharField(max_length=30)
    trail_length = MeasurementField(measurement=Distance)
    unique_id = models.CharField(max_length=100, unique=True)

    @classmethod
    def from_osm_trail_network(cls, osm_network: osm.model.TrailNetwork):
        return cls(
            name="Unknown",
            trail_length=osm_network.total_length(),
            unique_id=osm_network.unique_id()[:100],
        )


class Node(models.Model):
    point = models.PointField(geography=True)
    osm_id = models.BigIntegerField(primary_key=True)

    @property
    def lat(self):
        return self.point.y

    @property
    def lon(self):
        return self.point.x

    @property
    def elevation(self):
        return self.point.z

    def distance(self, other: "Point") -> Distance:
        return Distance(
            m=geopy.distance.great_circle(
                (self.lat, self.lon), (other.y, other.x)
            ).m
        )

    @classmethod
    def from_osm_node(cls, osm_node: osm.model.Node):
        return cls(point=Point(x=osm_node.lon, y=osm_node.lat), osm_id=osm_node.id)


class Trailhead(models.Model):
    trail_network = models.ForeignKey(TrailNetwork, on_delete=models.CASCADE)
    node = models.OneToOneField(Node, on_delete=models.CASCADE, unique=True)
    name = models.TextField(max_length=32)

    def draw(self, gmap):
        gmap.plot(
            [self.node.lat, self.node.lat + 0.0001],
            [self.node.lon, self.node.lon + 0.0001],
            edge_width=5,
        )

    @staticmethod
    def trailheads_near(pnt: Point, max_distance_km: float):
        return (
            Trailhead.objects.filter(
                node__point__dwithin=(pnt, D(m=max_distance_km * 1000))
            )
                .annotate(distance=GisDistance("node__point", pnt))
                .order_by("distance")
        )


class TravelCache(models.Model):
    start_point = models.PointField()


class TravelTime(models.Model):
    travel_time_minutes = models.FloatField()
    osm_id = models.BigIntegerField()
    start_point = models.ForeignKey(TravelCache, on_delete=models.CASCADE)


class Route(models.Model):
    trail_network = models.ForeignKey(TrailNetwork, on_delete=models.CASCADE)
    length = MeasurementField(measurement=Distance, db_index=True)
    elevation_gain = MeasurementField(measurement=Distance, db_index=True)
    elevation_loss = MeasurementField(measurement=Distance, db_index=True)
    is_loop = models.BooleanField()
    nodes = models.LineStringField(dim=3)
    trailhead = models.ForeignKey(Trailhead, db_index=True, on_delete=models.CASCADE)
    quality = models.FloatField()
    name = models.CharField(max_length=64, default="")
    osm_rep = models.BinaryField(default=None, null=True)

    @classmethod
    def from_subpath(
            cls,
            subpath: osm.model.Subpath,
            trail_network: TrailNetwork,
            trailhead: Trailhead,
    ):
        elev = subpath.elevation_change()
        elevations = osm.model.ElevationChange.elevations(subpath.nodes())
        return cls(
            trail_network=trail_network,
            length=Distance(m=subpath.length_m),
            elevation_gain=Distance(m=elev.gain),
            elevation_loss=Distance(m=elev.loss),
            is_loop=subpath.is_complete(),
            nodes=LineString([Point(node.lat, node.lon, 0) for (node, elev) in zip(subpath.nodes(), elevations)]),
            trailhead=trailhead,
            quality=subpath.quality(),
            osm_rep=pickle.dumps(subpath),
            name=subpath.name()
        )

    def add_elevations(self):
        osm_nodes = [osm.model.Node(id=-1, lon=node[1], lat=node[0]) for node in self.nodes]
        elevations = osm.model.ElevationChange.elevations(osm_nodes)
        new_nodes = [Point(node[0], node[1], elevation) for node, elevation in zip(self.nodes, elevations)]
        self.nodes = LineString(new_nodes)

    def to_gpx_segment(self):
        nodes = self.nodes
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        # Create points:
        for node in nodes:
            gpx_segment.points.append(
                gpxpy.gpx.GPXTrackPoint(latitude=node[0], longitude=node[1])
            )
        return gpx_segment

    def to_gpx(self):
        return self.to_gpx_segment().to_xml()

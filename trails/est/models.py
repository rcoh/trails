import re
import uuid
from datetime import datetime, timedelta

import geopy.distance
import gpxpy
import gpxpy.gpx
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django_measurement.models import MeasurementField
from measurement.measures import Distance

import osm.model


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Import(BaseModel):
    border = models.PolygonField()
    active = models.BooleanField()
    name = models.TextField(blank=True)


class TrailNetwork(BaseModel):
    source = models.ForeignKey(Import, on_delete=models.CASCADE, related_name='networks')
    name = models.TextField()
    # Just for rendering
    trails = models.MultiLineStringField(dim=2)
    poly = models.PolygonField(dim=2)
    total_length = MeasurementField(measurement=Distance)

    trailheads = models.MultiPointField(dim=2)

    # Pickled representation of the networkx graph
    graph = models.BinaryField()

    # Hex digest of the input nodes
    digest = models.TextField(default='')

    def clean_name(self):
        return re.sub(r'\W+', '', self.name)

    @classmethod
    def active(cls):
        return TrailNetwork.objects.filter(source__active=True)


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
            m=geopy.distance.great_circle((self.lat, self.lon), (other.y, other.x)).m
        )

    @classmethod
    def from_osm_node(cls, osm_node: osm.model.Node):
        return cls(point=Point(x=osm_node.lon, y=osm_node.lat), osm_id=osm_node.id)


NotStarted = 0
InProgress = 1
Complete = 2
Error = 3


class Circuit(BaseModel):
    route = models.LineStringField(dim=3, null=True)
    total_length = MeasurementField(measurement=Distance, null=True)
    network = models.ForeignKey(TrailNetwork, on_delete=models.CASCADE)

    status = models.IntegerField(
        choices=[(NotStarted, "not_started"), (InProgress, "in_progress"), (Complete, "complete"), (Error, "error")],
        default=2)
    error = models.TextField(blank=True)

    def to_gpx(self):
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        # Create first segment in our GPX track:

        # Create points:
        t = datetime.now()
        for (lng, lat, _) in self.route:
            t += timedelta(seconds=1)
            gpx_segment.points.append(
                gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lng, time=t)
            )
        return gpx.to_xml()

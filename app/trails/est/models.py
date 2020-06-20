import uuid

import geopy.distance
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


class TrailNetwork(BaseModel):
    name = models.TextField()
    # Just for rendering
    trails = models.MultiLineStringField(dim=2)
    bounding_box = models.PolygonField(dim=2)
    total_length = MeasurementField(measurement=Distance)

    # Pickled representation of the networkx graph
    graph = models.BinaryField()


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


class Circuit(BaseModel):
    route = models.LineStringField(dim=3)
    total_length = MeasurementField(measurement=Distance)
    network = models.ForeignKey(TrailNetwork, on_delete=models.CASCADE)

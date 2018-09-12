from django.core.validators import validate_comma_separated_integer_list
from django.db import models

# Create your models here.
import osm.model


# from osm.model import Subpath, TrailNetwork


class TrailNetwork(models.Model):
    name = models.CharField(max_length=30)
    # way_ids = models.TextField()
    trail_length_km = models.FloatField()
    unique_id = models.CharField(max_length=100, unique=True)

    @classmethod
    def from_osm_trail_network(cls, osm_network: osm.model.TrailNetwork):
        return cls(name='Unknown', trail_length_km=osm_network.total_length_km(), unique_id=osm_network.unique_id()[:100])

    # def matches(self, other_network):
    #     ourways = set(self.way_ids.split(','))
    #     theirways = set(other_network.way_ids.split(','))
    #     total_ways = max(len(ourways), len(theirways))
    #     overlap = ourways.intersection(theirways)
    #     if len(overlap) / total_ways > .8:
    #         return True
    # coordinates JSON serialized
    # coords = models.TextField()



class Node(models.Model):
    lat = models.FloatField()
    lon = models.FloatField()
    osm_id = models.PositiveIntegerField(primary_key=True)

    @classmethod
    def from_osm_node(cls, osm_node=osm.model.Node):
        return cls(lat=osm_node.lat, lon=osm_node.lon, osm_id=osm_node.id)


class Trailhead(models.Model):
    trail_network = models.ForeignKey(TrailNetwork, on_delete=models.CASCADE)
    node = models.OneToOneField(Node, on_delete=models.CASCADE, unique=True)

class Route(models.Model):
    trail_network = models.ForeignKey(TrailNetwork, on_delete=models.CASCADE)
    length_km = models.FloatField()
    elevation_gain = models.FloatField()
    elevation_loss = models.FloatField()
    is_loop = models.BooleanField()
    nodes = models.TextField(validators=[validate_comma_separated_integer_list])
    trailhead = models.ForeignKey(Trailhead, on_delete=models.CASCADE)

    @classmethod
    def from_subpath(cls, subpath: osm.model.Subpath, trail_network: TrailNetwork, trailhead: Trailhead):
        elev = subpath.elevation_change()
        node_rep = ','.join([str(n.id) for n in subpath.nodes()])
        return cls(trail_network=trail_network, length_km=subpath.length_km(), elevation_gain=elev.gain,
                   elevation_loss=elev.loss, is_loop=subpath.is_complete(), nodes=node_rep, trailhead=trailhead)

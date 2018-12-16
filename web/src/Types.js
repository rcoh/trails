import PropTypes from "prop-types";
export const MinMax = PropTypes.shape({
  min: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired
});

export const Node = PropTypes.shape({
  lat: PropTypes.number.isRequired,
  lon: PropTypes.number.isRequired,
  osm_id: PropTypes.string,
  icon: PropTypes.any
});

export const Trailhead = PropTypes.shape({
  node: Node.isRequired
});

export const Trail = PropTypes.shape({
  nodes: PropTypes.arrayOf(Node).isRequired,
  trailhead: Trailhead.isRequired
});

export const Ordering = {
  MinimizeElevation: { field: "elevation", asc: true },
  MaximizeElevation: { field: "elevation", asc: false },
  MinimizeTravelTime: { field: "travel", asc: true }
};

export const MinimizeElevation = "MinimizeElevation";
export const MaximizeElevation = "MaximizeElevation";
export const MinimizeTravelTime = "MinimizeTravelTime";

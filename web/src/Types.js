import PropTypes from "prop-types";
export const MinMax = PropTypes.shape({
  min: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired
});

export const Node = PropTypes.shape({
  lat: PropTypes.number.isRequired,
  lon: PropTypes.number.isRequired,
  osm_id: PropTypes.string
});

export const Trailhead = PropTypes.shape({
  node: Node.isRequired,
});


export const Trail = PropTypes.shape({
  nodes: PropTypes.arrayOf(Node).isRequired,
  trailhead: Trailhead.isRequired
});
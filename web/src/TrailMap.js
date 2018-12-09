import React from "react";
import { compose, withProps, lifecycle } from "recompose";
import "react-table/react-table.css";
import "./App.css";
import { GoogleMap, Marker, withGoogleMap, Polyline } from "react-google-maps";
import { Trail, Node } from "./Types";
import PropTypes from "prop-types";

/*global google*/

export const TrailMap = compose(
  withProps({
    loadingElement: <div style={{ height: `100%` }} />,
    containerElement: <div style={{ height: `400px` }} />,
    mapElement: <div style={{ height: `100%` }} />
  }),
  lifecycle({
    componentWillMount() {
      const that = this;
      this.setState({
        onMapMounted: ref => {
          that.setState({ mapRef: ref });
        }
      });
    },
    componentDidUpdate() {
      const bounds = new google.maps.LatLngBounds();
      if (this.props.trail) {
        this.props.trail.nodes.forEach(({ lat, lon }) => {
          const point = { lat, lng: lon };
          bounds.extend(point);
        });
      }
      if (this.props.markers) {
        this.props.markers.forEach(({ lat, lon }) => {
          const point = { lat, lng: lon };
          bounds.extend(point);
        });
      }
      window.setTimeout(() => this.state.mapRef.fitBounds(bounds), 100);
    }
  }),
  withGoogleMap
)(props => {
  let trail;
  let markerNodes = props.markers || [];
  if (props.trail) {
    const path = props.trail.nodes.map(({ lat, lon }) => {
      const point = { lat, lng: lon };
      return point;
    });
    trail = <Polyline path={path} options={{ strokeOpacity: 0.9 }} />;
    markerNodes.push(props.trail.trailhead.node);
  }
  let markers = markerNodes.map(node => (
    <Marker
      key={node.osm_id}
      position={{ lat: node.lat, lng: node.lon }}
      title={`OSM_ID: ${node.osm_id}`}
    />
  ));

  const map = (
    <GoogleMap
      ref={props.onMapMounted}
      defaultZoom={8}
      defaultCenter={{ lat: -34.397, lng: 150.644 }}
    >
      {trail}
      {markers}
    </GoogleMap>
  );

  return map;
});

TrailMap.propTypes = {
  trail: Trail,
  markers: PropTypes.arrayOf(Node)
};

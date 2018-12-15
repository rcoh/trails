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
      let nPoints = 0;
      if (this.props.trail) {
        this.props.trail.nodes.forEach(({ lat, lon }) => {
          const point = { lat, lng: lon };
          nPoints += 1;
          bounds.extend(point);
        });
      }
      if (this.props.markers) {
        this.props.markers.forEach(({ lat, lon }) => {
          const point = { lat, lng: lon };
          nPoints += 1;
          bounds.extend(point);
        });
      }
      if (nPoints === 1) {
        const center = bounds.getCenter();
        const delta = 0.01;
        const left = { lat: center.lat() - delta, lng: center.lng() - delta };
        const right = { lat: center.lat() + delta, lng: center.lng() + delta };
        bounds.extend(left);
        bounds.extend(right);
      }
      window.setTimeout(() => {
        this.state.mapRef.fitBounds(bounds);
      }, 100);
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
  let markers = markerNodes.map(node => {
    return (
      <Marker
        key={node.osm_id || node.lat + node.lon}
        position={{ lat: node.lat, lng: node.lon }}
        title={`OSM_ID: ${node.osm_id}`}
        style={{ height: "20px" }}
        icon={node.icon}
      />
    );
  });

  const map = (
    <GoogleMap
      ref={props.onMapMounted}
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

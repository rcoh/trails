
import React from "react";
import { compose, withProps, lifecycle } from "recompose";
import "react-table/react-table.css";
import "./App.css";
import { GoogleMap, Marker, withGoogleMap, Polyline } from "react-google-maps";
import "rc-slider/assets/index.css";

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
        window.setTimeout(() => this.state.mapRef.fitBounds(bounds), 100);
      }
    }
  }),
  withGoogleMap
)(props => {
  let trail;
  let marker;
  if (props.trail) {
    const path = props.trail.nodes.map(({ lat, lon }) => {
      const point = { lat, lng: lon };
      return point;
    });
    trail = <Polyline path={path} options={{ strokeOpacity: 0.9 }} />;
    const th_node = props.trail.trailhead.node;
    marker = (
      <Marker
        position={{ lat: th_node.lat, lng: th_node.lon }}
        title={`OSM_ID: ${th_node.osm_id}`}
      />
    );
  }

  const map = (
    <GoogleMap
      ref={props.onMapMounted}
      defaultZoom={8}
      defaultCenter={{ lat: -34.397, lng: 150.644 }}
    >
      {trail}
      {marker}
    </GoogleMap>
  );

  return map;
});

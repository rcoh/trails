import React, { Component } from "react";
import { compose, withProps, lifecycle } from "recompose";
import PropTypes from "prop-types";
import { Button } from "evergreen-ui";
import { ResultTable } from "./ResultTable";
import "react-table/react-table.css";
import "./App.css";
import Geosuggest from "react-geosuggest";
import { GoogleMap, Marker, withGoogleMap, Polyline } from "react-google-maps";
import "rc-slider/assets/index.css";
import { UnitSystems } from "./Util";
import { loadAPI } from "./Api";
import {
  SegmentedControl,
  Pane,
  Text,
  Card,
  TextInput,
  Spinner
} from "evergreen-ui";
import ElevationPlot from "./ElevationProfile";

/*global google*/
// Select address
// Show trailheads on map
//


const defaultPadding = {
  margin: ".5em"
};

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      location: { lat: 37.47463, lng: -122.23131 },
      distance: 5,
      unitSystem: "imperial"
    };
    this.onSuggestSelect = this.onSuggestSelect.bind(this);
    this.updateDistance = this.updateDistance.bind(this);
    this.loadHistogram = this.loadHistogram.bind(this);
    this.loadResults = this.loadResults.bind(this);
    this.onTrailSelect = this.onTrailSelect.bind(this);
  }
  onSuggestSelect(suggest) {
    if (suggest) {
      this.setState({
        location: suggest.location,
        trailIndex: undefined,
        histogram: undefined
      });
    }
  }

  onTrailSelect(index) {
    this.setState({ trailIndex: index });
  }

  updateDistance(event) {
    this.setState({
      distance: event.target.value
    });
  }

  render() {
    let histogram;
    if (this.state.histogram) {
      if (this.state.histogram.num_routes > 0) {
        histogram = (
          <ResultHistogram
            {...this.state.histogram}
            select={this.loadResults}
          />
        );
      } else {
        histogram = NoResults;
      }
    }
    let spinner;
    if (this.state.spinner) {
      spinner = (
        <Pane>
          <Spinner />
          <br />
        </Pane>
      );
    }

    let results;
    if (this.state.results) {
      const trail =
        this.state.trailIndex != null
          ? this.state.results.routes[this.state.trailIndex]
          : undefined;
      results = (
        <Card width="95%">
          <TrailMap trail={trail} />
          <ElevationPlot units={this.state.results.units} trail={trail} />
          <ResultTable
            origin={this.state.location}
            results={this.state.results.routes}
            units={this.state.results.units}
            onSelect={this.onTrailSelect}
            rowIndex={this.state.trailIndex}
          />
        </Card>
      );
    }
    const unit = this.state.unitSystem;
    const unitOptions = [
      { label: "miles", value: "imperial" },
      { label: "kilometers", value: "metric" }
    ];
    const rowStyle = {
      marginTop: "3px",
      marginBottom: "3px"
    };
    return (
      <Pane display="flex" alignItems="center" flexDirection="column">
        <div
          className="top-container"
          /*width="28em"
          height="5em"
          display="flex"
          justifyContent="space-between"
          flexDirection="column"*/
        >
          <Pane
            display="flex"
            flexWrap="wrap"
            justifyContent="center"
            alignItems="center"
            {...rowStyle}
          >
            <Text {...defaultPadding}>Starting from:</Text>
            <Pane {...defaultPadding}>
              <Geosuggest
                onSuggestSelect={this.onSuggestSelect}
                renderSuggestItem={suggest => <Text>{suggest.label}</Text>}
              />
            </Pane>
          </Pane>
          <Pane
            display="flex"
            justifyContent="space-around"
            alignItems="center"
            flexWrap="wrap"
            {...rowStyle}
          >
            <Text {...defaultPadding}>I want to hike/run about</Text>
            <Pane display="flex" alignItems="center">
              <TextInput
                {...defaultPadding}
                value={this.state.distance}
                width="3em"
                onChange={this.updateDistance}
              />
              <SegmentedControl
                {...defaultPadding}
                width={150}
                options={unitOptions}
                value={unit}
                onChange={value =>
                  this.setState({
                    unitSystem: value,
                    histogram: undefined,
                    results: undefined
                  })
                }
              />
            </Pane>
            <Button
              flex="auto"
              justifyContent="center"
              appearance="primary"
              onClick={this.loadHistogram}
            >
              <Pane display="flex" justifyContent="center">
                Go
              </Pane>
            </Button>
          </Pane>
        </div>
        {histogram}
        <hr />
        {spinner}
        {results}
      </Pane>
    );
  }

  async loadResults(ordering) {
    const loc = {
      location_filter: {
        lat: this.state.location.lat,
        lon: this.state.location.lng
      },
      length: {
        value: this.state.distance,
        tolerance: 0.1
      },
      units: this.state.unitSystem,
      ordering
    };
    this.setState({ spinner: true });
    const trails = await loadAPI("trails/", loc);
    this.setState({
      spinner: false,
      results: trails,
      trailIndex: trails.routes.length > 0 ? 0 : undefined
    });
  }

  async loadHistogram(event) {
    const loc = {
      location_filter: {
        lat: this.state.location.lat,
        lon: this.state.location.lng
      },
      length: {
        value: this.state.distance,
        tolerance: 0.1
      },
      units: this.state.unitSystem
    };
    this.setState({ spinner: true });
    const histogram = await loadAPI("histogram/", loc);
    this.setState({ spinner: false, histogram, results: undefined });
  }
}


const minMax = PropTypes.shape({
  min: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired
});

const minimizeElevation = { field: "elevation", asc: true };
const maximizeElevation = { field: "elevation", asc: false };
const minimizeTravelTime = { field: "travel", asc: true };

const NoResults = (
  <Card>
    <Text>Sorry, there aren't any results matching your search. TrailsTo.run currently only has data from the United States.</Text>
  </Card>
);
class ResultHistogram extends Component {
  render() {
    const u = UnitSystems[this.props.units];
    return (
      <Pane
        display="flex"
        alignItems="center"
        flexWrap="wrap"
        justifyContent="center"
      >
        <Button
          {...defaultPadding}
          onClick={() => this.props.select(minimizeElevation)}
        >
          Flattest ({this.props.elevation.min.toFixed(0)} {u.height.long})
        </Button>
        <Button
          {...defaultPadding}
          onClick={() => this.props.select(maximizeElevation)}
        >
          Hilliest ({this.props.elevation.max.toFixed(0)} {u.height.long})
        </Button>
        <Button
          {...defaultPadding}
          onClick={() => this.props.select(minimizeTravelTime)}
        >
          Closest ({(this.props.travel_time.min / 60).toFixed(0)} minutes)
        </Button>
      </Pane>
    );
  }
}

ResultHistogram.propTypes = {
  elevation: minMax.isRequired,
  distance: minMax.isRequired,
  travel_time: minMax.isRequired,
  select: PropTypes.func.isRequired,
  units: PropTypes.string.isRequired
};

const TrailMap = compose(
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

export default App;

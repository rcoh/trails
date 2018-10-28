import React, { Component } from "react";
import { compose, withProps, lifecycle } from "recompose";
import PropTypes from "prop-types";
import { Button } from "evergreen-ui";
import ReactTable from "react-table";
import "react-table/react-table.css";
import "./App.css";
import Geosuggest from "react-geosuggest";
import { GoogleMap, Marker, withGoogleMap, Polyline } from "react-google-maps";
import Slider, { Range } from "rc-slider";
import "rc-slider/assets/index.css";
import { SegmentedControl, Pane, Text, Card, TextInput } from "evergreen-ui";

/*global google*/
const server = process.env["REACT_APP_SERVER"] || "http://localhost:8000";
// Select address
// Show trailheads on map
//

const Units = {
  km: {
    long: "kilometers",
    short: "km"
  },
  mi: {
    long: "miles",
    short: "miles"
  },
  m: {
    long: "meters",
    short: "m"
  },
  ft: {
    long: "feet",
    short: "ft"
  }
};

const UnitSystems = {
  metric: {
    length: Units.km,
    height: Units.m,
    name: "metric"
  },
  imperial: {
    name: "imperial",
    length: Units.mi,
    height: Units.ft
  }
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
          <Card width="28em">
            <ResultHistogram
              {...this.state.histogram}
              select={this.loadResults}
            />
          </Card>
        );
      } else {
        histogram = NoResults;
      }
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
          <ResultTable
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
      marginTop: "5px",
      marginBottom: "5px"
    };
    return (
      <Pane display="flex" alignItems="center" flexDirection="column">
        <Card
          width="28em"
          height="5em"
          display="flex"
          justifyContent="space-between"
          flexDirection="column"
        >
          <Pane
            display="flex"
            justifyContent="space-around"
            alignItems="center"
            {...rowStyle}
          >
            <Text>Starting from:</Text>
            <Geosuggest onSuggestSelect={this.onSuggestSelect} />
          </Pane>
          <Pane
            display="flex"
            justifyContent="space-around"
            alignItems="center"
            {...rowStyle}
          >
            <Text>I want to hike/run about</Text>
            <TextInput
              value={this.state.distance}
              width="3em"
              onChange={this.updateDistance}
            />
            <SegmentedControl
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
            <Button color="primary" onClick={this.loadHistogram}>
              Go
            </Button>
          </Pane>
        </Card>
        <hr />
        {histogram}
        <hr />
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
        tolerance: 1
      },
      units: this.state.unitSystem,
      ordering
    };
    const trails = await loadAPI("trails/", loc);
    this.setState({
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
        tolerance: 1
      },
      units: this.state.unitSystem
    };
    const histogram = await loadAPI("histogram/", loc);
    this.setState({ histogram, results: undefined });
  }
}

const loadAPI = async (endpoint, data) => {
  const resp = await fetch(`${server}/api/${endpoint}`, {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json"
    }
  });
  if (!resp.ok) {
    throw Error(JSON.stringify(await resp.json()));
  }
  return await resp.json();
};

const minMax = PropTypes.shape({
  min: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired
});

const minimizeElevation = { field: "elevation", asc: true };
const maximizeElevation = { field: "elevation", asc: false };
const minimizeTravelTime = { field: "travel", asc: true };

const NoResults = (
  <Card><Text>Sorry, there aren't any results matching your search</Text></Card>
);
class ResultHistogram extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    const marks = {};
    const u = UnitSystems[this.props.units];
    return (
      <Pane display="flex" justifyContent="space-between">
        <Button
          color="success"
          onClick={() => this.props.select(minimizeElevation)}
        >
          Flattest ({this.props.elevation.min.toFixed(0)} {u.height.long})
        </Button>
        <Button
          color="success"
          onClick={() => this.props.select(maximizeElevation)}
        >
          Hilliest ({this.props.elevation.max.toFixed(0)} {u.height.long})
        </Button>
        <Button
          color="success"
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
  elevations: PropTypes.array.isRequired,
  distance: minMax.isRequired,
  travel_time: minMax.isRequired,
  select: PropTypes.func.isRequired,
  units: PropTypes.object.isRequired
};

class ResultTable extends Component {
  constructor(props) {
    super(props);
    this.state = { selected: undefined };
  }

  componentDidUpdate(prevProps, prevState, snapshot) {
    if (prevProps.results != this.props.results) {
      this.setState({ selected: undefined });
    }
  }

  downloadFile(props) {}
  u = UnitSystems[this.props.units];
  columns = [
    {
      Header: `Length (${this.u.length.short})`,
      accessor: "length"
      //Cell: props => props.value.toFixed(1)
    },
    {
      Header: `Elevation Gain (${this.u.height.short})`,
      accessor: "elevation_gain",
      Cell: props => props.value.toFixed(0)
    },
    {
      Header: "Drive Time (minutes)",
      accessor: "travel_time"
    },
    {
      Header: "Export Gpx",
      accessor: "id",
      Cell: props => (
        <div>
          <button
            onClick={() =>
              (window.location.href = `${server}/api/export/?id=${props.value}`)
            }
          >
            Export GPX
          </button>
        </div>
      )
    }
  ];

  selectedIndex() {
    return this.state.selected || this.props.rowIndex;
  }

  render() {
    const that = this;
    return (
      <ReactTable
        data={this.props.results}
        columns={this.columns}
        getTrProps={(state, rowInfo) => {
          if (rowInfo && rowInfo.row) {
            return {
              onClick: e => {
                that.setState({
                  selected: rowInfo.index
                });
                that.props.onSelect(rowInfo.index);
              },
              style: {
                background:
                  rowInfo.index === this.selectedIndex() ? "#00afec" : "white",
                color:
                  rowInfo.index === this.selectedIndex() ? "white" : "black",
                cursor: "pointer"
              }
            };
          } else {
            return {};
          }
        }}
      />
    );
  }
}

ResultTable.propTypes = {
  units: PropTypes.object.isRequired,
  results: PropTypes.array.isRequired,
  onSelect: PropTypes.func.isRequired
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

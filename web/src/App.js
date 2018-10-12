import React, { Component } from "react";
import { compose, withProps, lifecycle } from "recompose";
import PropTypes from "prop-types";
import { Button } from 'reactstrap';
import ReactTable from "react-table";
import "react-table/react-table.css";
import "./App.css";
import Geosuggest from "react-geosuggest";
import { GoogleMap, Marker, withGoogleMap, Polyline } from "react-google-maps";
import Slider, { Range } from "rc-slider";
import "rc-slider/assets/index.css";

/*global google*/
const server = process.env["REACT_APP_SERVER"] || "http://localhost:8000";
// Select address
// Show trailheads on map
//

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      location: { lat: 37.47463, lng: -122.23131 },
      distance: 5
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
      distance: event.target.value,
    });
  }

  render() {
    let histogram;
    if (this.state.histogram) {
      histogram = (
        <ResultHistogram {...this.state.histogram} select={this.loadResults} />
      );
    }

    let results;
    if (this.state.results) {
      const trail =
        this.state.trailIndex != null
          ? this.state.results[this.state.trailIndex]
          : undefined;
      results = (
        <div>
          <TrailMap trail={trail} />
          <ResultTable
            results={this.state.results}
            onSelect={this.onTrailSelect}
            rowIndex={this.state.trailIndex}
          />
        </div>
      );
    }
    return (
      <div className="App container">
        <div>
          Starting from: <Geosuggest onSuggestSelect={this.onSuggestSelect} />
        </div>
        I want to hike/run about
        <input
          className="distance-input"
          value={this.state.distance}
          onChange={this.updateDistance}
        />
        kilometers
        <Button color="primary" onClick={this.loadHistogram}>Go</Button>
        {histogram}
        {results}
      </div>
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
      ordering
    };
    const trails = await loadAPI("trails/", loc);
    this.setState({
      results: trails,
      trailIndex: trails.length > 0 ? 0 : undefined
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
      }
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

const SliderT = Slider.createSliderWithTooltip(Slider);
const sliderStyle = {
  width: "30%"
};

class ResultHistogram extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    const marks = {};
    this.props.elevations.forEach(v => {
      marks[v] = "";
    });

    //<SliderT min={this.props.elevation.min} max={this.props.elevation.max} style={sliderStyle} marks={marks}/>
    return (
      <div class="select-buttons">
        <Button color="success" onClick={() => this.props.select(minimizeElevation)}>
          Flatest ({this.props.elevation.min.toFixed(0)} meters)
        </Button>
        <Button color="success" onClick={() => this.props.select(maximizeElevation)}>
          Hilliest ({this.props.elevation.max.toFixed(0)} meters)
        </Button>
        <Button color="success" onClick={() => this.props.select(minimizeTravelTime)}>
          Minimize drive time ({(this.props.travel_time.min / 60).toFixed(0)}{" "}
          minutes)
        </Button>
      </div>
    );
  }
}

ResultHistogram.propTypes = {
  elevation: minMax.isRequired,
  elevations: PropTypes.array.isRequired,
  distance: minMax.isRequired,
  travel_time: minMax.isRequired,
  select: PropTypes.func.isRequired
};

class ResultTable extends Component {
  constructor(props) {
    super(props);
    this.state = { selected: undefined };
  }

  componentDidUpdate(prevProps, prevState, snapshot) {
    if (prevProps.results != this.props.results) {
      this.setState({selected: undefined});
    }
  }

  downloadFile(props) {}
  columns = [
    {
      Header: "Length (km)",
      accessor: "length_km",
      Cell: props => props.value.toFixed(1)
    },
    {
      Header: "Elevation Gain (m)",
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

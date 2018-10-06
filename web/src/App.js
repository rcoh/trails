import React, { Component } from "react";
import { compose, withProps, lifecycle } from "recompose";
import PropTypes from "prop-types";
import logo from "./logo.svg";
import ReactTable from "react-table";
import "react-table/react-table.css";
import "./App.css";
import Geosuggest from "react-geosuggest";
import { GoogleMap, Marker, withGoogleMap, Polyline } from "react-google-maps";
import Slider, { Range } from 'rc-slider';
import 'rc-slider/assets/index.css';

/*global google*/
const server = process.env['REACT_APP_SERVER'] || 'http://localhost:8000';
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
    this.setState({ location: suggest.location });
  }

  onTrailSelect(index) {
    this.setState({ trailIndex: index });
  }

  updateDistance(event) {
    this.setState({ distance: event.target.value });
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
          ? this.state.results[this.state.trailIndex].nodes
          : undefined;
      results = (
        <div>
          <TrailMap trail={trail} />
          <ResultTable
            results={this.state.results}
            onSelect={this.onTrailSelect}
          />
        </div>
      );
    }
    return (
      <div className="App">
        <div>
          Starting from: <Geosuggest onSuggestSelect={this.onSuggestSelect} />
        </div>
        I want to hike/run about
        <input
          type="number"
          value={this.state.distance}
          onChange={this.updateDistance}
        />
        kilometers
        <button onClick={this.loadHistogram}>Go</button>
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
    this.setState({ results: trails });
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
    this.setState({ histogram });
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
  width: '30%'
}

class ResultHistogram extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    const marks = {};
    this.props.elevations.forEach(v => {marks[v] = ''});

    //<SliderT min={this.props.elevation.min} max={this.props.elevation.max} style={sliderStyle} marks={marks}/>
    return (
      <div>
        <button onClick={() => this.props.select(minimizeElevation)}>
          Minimize elevation ({this.props.elevation.min} meters)
        </button>
        <button onClick={() => this.props.select(maximizeElevation)}>
          Maximize elevation ({this.props.elevation.max} meters)
        </button>
        <button onClick={() => this.props.select(minimizeTravelTime)}>
          Minimize travel time ({Math.round(this.props.travel_time.min / 60)}{" "}
          minutes)
        </button>
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
    this.state = { selected: null };
  }

  downloadFile(props) {
  }
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
        Header: "Travel Time (minutes)",
        accessor: "travel_time"
      },
      {
        Header: "Export Gpx",
        accessor: "id",
        Cell: props =>
	<div>
		<button onClick={() => window.location.href=`${server}/api/export/?id=${props.value}`}>
                    Export GPX
		</button>	
	</div>
      },
  ];

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
                  rowInfo.index === this.state.selected ? "#00afec" : "white",
                color:
                  rowInfo.index === this.state.selected ? "white" : "black",
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
        this.props.trail.forEach(({ lat, lon }) => {
          const point = { lat, lng: lon };
          bounds.extend(point);
        });
        this.state.mapRef.fitBounds(bounds);
      }
    }
  }),
  withGoogleMap
)(props => {
  let trail;
  let marker;
  if (props.trail) {
    const path = props.trail.map(({ lat, lon }) => {
      const point = { lat, lng: lon };
      return point;
    });
    trail = <Polyline path={path} options={{strokeOpacity: 0.2}} />;
    marker = (
      <Marker position={{ lat: props.trail[0].lat, lng: props.trail[0].lon }} />
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

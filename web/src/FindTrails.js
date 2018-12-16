import React, { Component } from "react";
import { Button } from "evergreen-ui";
import { ResultTable } from "./ResultTable";
import "react-table/react-table.css";
import "./App.css";
import { LocationSelect } from "./LocationSelect";
import { loadAPI } from "./Api";
import ReactGA from "react-ga";
import {
  SegmentedControl,
  Pane,
  Text,
  Card,
  Heading,
  TextInput,
  Spinner
} from "evergreen-ui";
import ElevationPlot from "./ElevationProfile";
import ResultHistogram from "./ResultHistogram";
import { DefaultPadding, RowStyle } from "./Styles";
import { TrailMap } from "./TrailMap";
import { Ordering } from "./Types";

const defaultLocation = () => {
  // Set a default value when running locally for easy testing
  return {};
  /*if (process.env["NODE_ENV"] === "development") {
    return { lat: 37.47463, lng: -122.23131 };
  } else return {};*/
};

class FindTrails extends Component {
  constructor(props) {
    super(props);
    this.state = {
      location: defaultLocation(),
      distance: 5,
      unitSystem: "imperial",
      ordering: undefined
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
        histogram: undefined,
        ordering: undefined
      });
      this.loadHistogram();
    }
  }

  onTrailSelect(index) {
    this.setState({ trailIndex: index });
  }

  updateDistance(event) {
    const that = this;
    this.setState(
      {
        distance: event.target.value,
        ordering: undefined
      },
      () => {
        if (!isNaN(parseFloat(that.state.distance))) {
          that.loadHistogram();
        }
      }
    );
  }

  renderHistogram() {
    if (!this.state.histogram) {
      return;
    }
    if (this.state.histogram.num_routes === 0) {
      return NoResults;
    } else {
      return (
        <ResultHistogram
          selected={this.state.ordering}
          {...this.state.histogram}
          select={this.loadResults}
        />
      );
    }
  }

  renderSpinner() {
    if (this.state.spinner) {
      return (
        <Pane>
          <Spinner />
          <br />
        </Pane>
      );
    } else {
      return;
    }
  }

  renderResults() {
    if (!this.state.results) {
      if (this.state.histogram) {
        const currentLocation = {
          lat: this.state.location.lat,
          lon: this.state.location.lng,
          icon: {
            url: "/running-solid.svg",
            scaledSize: { width: 30, height: 30 }
          }
        };
        const trailheads = (this.state.histogram.trailheads || []).map(
          trailhead => {
            return {
              lat: trailhead.node.lat,
              lon: trailhead.node.lon
            };
          }
        );
        const markers = [currentLocation, ...trailheads];
        return (
          <Card width="95%">
            <TrailMap markers={markers} />
          </Card>
        );
      }
      return (
        <Card width="95%">
          <TrailMap />
        </Card>
      );
    }
    const trail =
      this.state.trailIndex != null
        ? this.state.results.routes[this.state.trailIndex]
        : undefined;

    return (
      <Card width="95%">
        <TrailMap trail={trail} />
        <ElevationPlot units={this.state.results.units} trail={trail} />
        <ResultTable
          origin={this.state.location}
          results={this.state.results.routes}
          units={this.state.results.units}
          onSelect={this.onTrailSelect}
          //rowIndex={this.state.trailIndex}
        />
      </Card>
    );
  }

  render() {
    const histogram = this.renderHistogram();
    const spinner = this.renderSpinner();
    const results = this.renderResults();

    const unit = this.state.unitSystem;
    const unitOptions = [
      { label: "miles", value: "imperial" },
      { label: "kilometers", value: "metric" }
    ];
    return (
      // Outer level container
      <Pane display="flex" alignItems="center" flexDirection="column">
        <Heading size={800} marginBottom="default">
          Find trails to run near you
        </Heading>
        <LocationSelect onSelect={this.onSuggestSelect} />
        <Pane
          display="flex"
          justifyContent="space-around"
          alignItems="center"
          flexWrap="wrap"
          {...RowStyle}
        >
          <Text {...DefaultPadding}>I want to hike/run about</Text>
          <Pane display="flex" alignItems="center">
            <TextInput
              {...DefaultPadding}
              value={this.state.distance}
              width="3em"
              onChange={this.updateDistance}
            />
            <SegmentedControl
              {...DefaultPadding}
              width={150}
              options={unitOptions}
              value={unit}
              onChange={value => {
                this.setState(
                  {
                    unitSystem: value,
                    histogram: undefined,
                    results: undefined,
                    ordering: undefined
                  },
                  this.loadHistogram
                );
              }}
            />
          </Pane>
        </Pane>
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
      ordering: Ordering[ordering]
    };
    this.setState({ spinner: true });
    const trails = await loadAPI("trails/", loc);
    this.setState({
      spinner: false,
      results: trails,
      trailIndex: trails.routes.length > 0 ? 0 : undefined,
      ordering: ordering
    });
    ReactGA.event({ category: "trails", action: "Load Results" });
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
    ReactGA.event({ category: "trails", action: "Load Histogram" });
    //this.loadResults(DefaultOrdering);
  }
}

const NoResults = (
  <Card>
    <Text>
      Sorry, there aren't any results matching your search. TrailsTo.run
      currently only has data from the United States.
    </Text>
  </Card>
);

export default FindTrails;

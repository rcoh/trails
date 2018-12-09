import React, { Component } from "react";
import { Button } from "evergreen-ui";
import { TrailheadTable } from "./TrailheadTable";
import { LocationSelect } from "./LocationSelect";
import { DefaultPadding, RowStyle } from "./Styles";
import "react-table/react-table.css";
import "./App.css";
import { nearbyTrailheads } from "./Api";
import { Pane, Text, Card, TextInput, Spinner } from "evergreen-ui";
import { TrailMap } from "./TrailMap";
import { UnitSystems } from "./Util";
import ReactGA from 'react-ga';

export default class Explore extends Component {
  constructor(props) {
    super(props);
    this.state = {
      travelTime: 20,
      unitSystem: "imperial",
      spinner: false,
    };
    this.updateTravelTime = this.updateTravelTime.bind(this);
    this.onLocationSelect = this.onLocationSelect.bind(this);
    this.search = this.search.bind(this);
  }

  onLocationSelect(suggest) {
    if (suggest) {
      this.setState({
        location: suggest.location,
        trailIndex: undefined,
        histogram: undefined
      });
    }
  }

  updateTravelTime(event) {
    this.setState({
      travelTime: event.target.value
    });
  }

  async search() {
    this.setState({spinner: true});
    const results = await nearbyTrailheads({
      location: this.state.location,
      max_travel_time_minutes: this.state.travelTime,
      units: UnitSystems.imperial.name
    });
    this.setState({ results, spinner: false });
    ReactGA.event({category: "explore", action: "Load Results"});
  }

  renderSpinner() {
    if (this.state.spinner) {
      return <Spinner />;
    } else{
      return;
    }
  }

  renderResults() {
    const { results } = this.state;
    if (!results) {
      return;
    }
    const markers = results.map(result => {
      const { trailhead } = result;
      return trailhead.node;
    });
    return (
      <Card width="95%">
        <TrailMap markers={markers} />
        <TrailheadTable
          results={results}
          units={UnitSystems.imperial.name}
          origin={this.state.location}
          onSelect={() => {}}
        />
      </Card>
    );
  }

  render() {
    return (
      <Pane display="flex" alignItems="center" flexDirection="column">
        <LocationSelect onSelect={this.onLocationSelect} />
        <Pane
          display="flex"
          justifyContent="space-around"
          alignItems="center"
          flexWrap="wrap"
          {...RowStyle}
        >
          <Text {...DefaultPadding}>Show me trailheads with in a</Text>
          <Pane display="flex" alignItems="center">
            <TextInput
              {...DefaultPadding}
              value={this.state.travelTime}
              width="3em"
              onChange={this.updateTravelTime}
            />
            <Text {...DefaultPadding}>minute drive</Text>
          </Pane>
          <Button
            flex="auto"
            justifyContent="center"
            appearance="primary"
            disabled={this.state.location == null}
            onClick={this.search}
          >
            <Pane display="flex" justifyContent="center">
              Go
            </Pane>
          </Button>
        </Pane>
        {this.renderSpinner()}
        {this.renderResults()}
      </Pane>
    );
  }
}

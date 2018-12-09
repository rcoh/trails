import React, { Component } from "react";
import PropTypes from "prop-types";
import { Button } from "evergreen-ui";
import "react-table/react-table.css";
import { UnitSystems } from "./Util";
import { Pane } from "evergreen-ui";
import { DefaultPadding } from "./Styles";
import { MinMax } from "./Types";

const minimizeElevation = { field: "elevation", asc: true };
const maximizeElevation = { field: "elevation", asc: false };
const minimizeTravelTime = { field: "travel", asc: true };

export default class ResultHistogram extends Component {
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
          {...DefaultPadding}
          onClick={() => this.props.select(minimizeElevation)}
        >
          Flattest ({this.props.elevation.min.toFixed(0)} {u.height.long})
        </Button>
        <Button
          {...DefaultPadding}
          onClick={() => this.props.select(maximizeElevation)}
        >
          Hilliest ({this.props.elevation.max.toFixed(0)} {u.height.long})
        </Button>
        <Button
          {...DefaultPadding}
          onClick={() => this.props.select(minimizeTravelTime)}
        >
          Closest ({(this.props.travel_time.min / 60).toFixed(0)} minutes)
        </Button>
      </Pane>
    );
  }
}

ResultHistogram.propTypes = {
  elevation: MinMax.isRequired,
  distance: MinMax.isRequired,
  travel_time: MinMax.isRequired,
  select: PropTypes.func.isRequired,
  units: PropTypes.string.isRequired
};

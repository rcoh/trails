import React, { Component } from "react";
import PropTypes from "prop-types";
import { SegmentedControl } from "evergreen-ui";
import "react-table/react-table.css";
import { UnitSystems } from "./Util";
import { Pane } from "evergreen-ui";
import { DefaultPadding } from "./Styles";
import {
  MinMax,
  MinimizeElevation,
  MaximizeElevation,
  MinimizeTravelTime
} from "./Types";

const twoLine = (top, bottom) => (
  <Pane
    paddingTop="4px"
    paddingBottom="4px"
    display="flex"
    alignItems="center"
    flexWrap="wrap"
    justifyContent="center"
  >
    <Pane key="top" paddingLeft="0.5em" paddingRight="0.5em">
      {top}
    </Pane>
    <Pane key="bottom">{bottom}</Pane>
  </Pane>
);

export default class ResultHistogram extends Component {
  render() {
    const u = UnitSystems[this.props.units];
    const choiceOptions = [
      {
        label: twoLine(
          "Hilliest",
          `(${this.props.elevation.max.toFixed(0)} ${u.height.long})`
        ),
        value: MaximizeElevation
      },
      //{ label: "Medium hilly", value: MaximizeElevation },
      {
        label: twoLine(
          "Flattest",
          `(${this.props.elevation.min.toFixed(0)} ${u.height.long})`
        ),
        value: MinimizeElevation
      },
      {
        label: twoLine(
          "Closest",
          `(${(this.props.travel_time.min / 60).toFixed(0)} minutes)`
        ),
        value: MinimizeTravelTime
      }
    ];
    return (
      <Pane
        display="flex"
        alignItems="center"
        flexWrap="wrap"
        justifyContent="center"
        width="95%"
      >
        <SegmentedControl
          {...DefaultPadding}
          width={"100%"}
          maxWidth={500}
          height={36}
          options={choiceOptions}
          value={this.props.selected || "none"}
          onChange={value => this.props.select(value)}
        />
      </Pane>
    );
  }
}

ResultHistogram.propTypes = {
  elevation: MinMax.isRequired,
  distance: MinMax.isRequired,
  travel_time: MinMax.isRequired,
  select: PropTypes.func.isRequired,
  units: PropTypes.string.isRequired,
  selected: PropTypes.string,
};

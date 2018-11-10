import React, { Component } from "react";
import PropTypes from "prop-types";
import { server } from "./Api";
import "react-table/react-table.css";
import "./App.css";
import "rc-slider/assets/index.css";
import { UnitSystems } from "./Util";
import { Pane, Text } from "evergreen-ui";
import ReactTable from "react-table";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDirections, faDownload } from "@fortawesome/free-solid-svg-icons";

export class ResultTable extends Component {
  constructor(props) {
    super(props);
    this.state = { selected: undefined };
  }

  componentDidUpdate(prevProps, prevState, snapshot) {
    if (prevProps.results !== this.props.results) {
      this.setState({ selected: undefined });
    }
  }

  downloadFile(props) {}
  u = UnitSystems[this.props.units];
  columns = [
    {
      Header: <Text>{`Length (${this.u.length.short})`}</Text>,
      accessor: "length",
      minWidth: 60,
      Cell: props => <Text>{props.value}</Text>
    },
    {
      Header: <Text>{`Elevation Gain (${this.u.height.short})`}</Text>,
      accessor: "elevation_gain",
      minWidth: 60,
      Cell: props => <Text>{props.value}</Text>
    },
    {
      Header: <Text>Drive Time (minutes)</Text>,
      accessor: "travel_time",
      minWidth: 60,
      Cell: props => <Text>{props.value}</Text>
    },
    {
      Header: <Text>Run it!</Text>,
      accessor: "id",
      maxWidth: 80,
      Cell: props => {
        const origin = `${this.props.origin.lat},${this.props.origin.lng}`;
        const trailhead = props.row._original.trailhead.node;
        const dest = `${trailhead.lat},${trailhead.lon}`;
        return (
          <Pane display="flex" justifyContent="space-around">
            <FontAwesomeIcon
              icon={faDirections}
              onClick={() =>
                window.open(
                  `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${dest}`
                )
              }
            />

            <FontAwesomeIcon
              icon={faDownload}
              onClick={() =>
                (window.location.href = `${server}/api/export/?id=${props.value}`)
              }
            />
          </Pane>
        );
      }
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
  units: PropTypes.oneOf(Object.keys(UnitSystems)),
  results: PropTypes.array.isRequired,
  onSelect: PropTypes.func.isRequired
};

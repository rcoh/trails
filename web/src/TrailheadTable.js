import React from "react";
import PropTypes from "prop-types";
import "react-table/react-table.css";
import "./App.css";
import { UnitSystems } from "./Util";
import { Pane, Text } from "evergreen-ui";
import SelectableTable from "./SelectableTable";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDirections } from "@fortawesome/free-solid-svg-icons";
import { Node } from "./Types";
import ReactGA from "react-ga";

export class TrailheadTable extends SelectableTable {
  u = UnitSystems[this.props.units];
  columns = [
    {
      Header: <Text>Name</Text>,
      accessor: "trailhead.name",
      minWidth: 60,
      Cell: props => <Text>{props.value}</Text>
    },
    {
      Header: <Text>Trail Network Length ({this.u.length.short})</Text>,
      accessor: "trail_network_length",
      minWidth: 60,
      Cell: props => <Text>{props.value}</Text>
    },
    {
      Header: <Text>Drive Time (minutes)</Text>,
      accessor: "travel_time_seconds",
      minWidth: 60,
      Cell: props => <Text>{Math.round(props.value / 60)}</Text>
    },
    {
      Header: <Text>Navigate</Text>,
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
              onClick={() => {
                ReactGA.event({ category: "explore", action: "navigate" });
                window.open(
                  `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${dest}`
                );
              }}
            />
          </Pane>
        );
      }
    }
  ];
}

TrailheadTable.propTypes = {
  units: PropTypes.oneOf(Object.keys(UnitSystems)),
  results: PropTypes.array.isRequired,
  origin: Node.isRequired,
  onSelect: PropTypes.func.isRequired
};

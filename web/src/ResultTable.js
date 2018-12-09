import React from "react";
import PropTypes from "prop-types";
import { server } from "./Api";
import "react-table/react-table.css";
import "./App.css";
import ReactGA from "react-ga";
import { UnitSystems } from "./Util";
import { Pane, Text } from "evergreen-ui";
import SelectableTable from "./SelectableTable";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDirections, faDownload } from "@fortawesome/free-solid-svg-icons";

export class ResultTable extends SelectableTable {
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
              onClick={() => {
                ReactGA.event({ category: "trails", action: "Navigate" });
                window.open(
                  `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${dest}`
                );
              }}
            />

            <FontAwesomeIcon
              icon={faDownload}
              onClick={() => {
                ReactGA.event({ category: "trails", action: "export" });
                window.location.href = `${server}/api/export/?id=${
                  props.value
                }`;
              }}
            />
          </Pane>
        );
      }
    }
  ];
}

ResultTable.propTypes = {
  units: PropTypes.oneOf(Object.keys(UnitSystems)),
  results: PropTypes.array.isRequired,
  onSelect: PropTypes.func.isRequired
};

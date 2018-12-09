import React, { Component } from "react";
import "react-table/react-table.css";
import "./App.css";
import ReactTable from "react-table";

export default class SelectableTable extends Component {
  constructor(props) {
    super(props);
    this.state = { selected: props.results ? 0 : undefined };
  }
  componentDidUpdate(prevProps, prevState, snapshot) {
    if (prevProps.results !== this.props.results) {
      this.setState({ selected: this.props.results ? 0 : undefined });
    }
  }

  selectedIndex() {
    return this.state.selected;
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

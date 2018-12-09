import React from "react";
import "react-table/react-table.css";
import "./App.css";
import Geosuggest from "react-geosuggest";
import {
  Pane,
  Text,
} from "evergreen-ui";
import { DefaultPadding, RowStyle } from "./Styles";

export const LocationSelect = props => {
  return <Pane
    display="flex"
    flexWrap="wrap"
    justifyContent="center"
    alignItems="center"
    {...RowStyle}
  >
    <Text {...DefaultPadding}>Starting from:</Text>
    <Pane {...DefaultPadding}>
      <Geosuggest
        onSuggestSelect={props.onSelect}
        renderSuggestItem={suggest => <Text>{suggest.label}</Text>}
      />
    </Pane>
  </Pane>;
};

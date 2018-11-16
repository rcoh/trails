import React from "react";

import {
  FlexibleWidthXYPlot,
  XAxis,
  YAxis,
  VerticalGridLines,
  HorizontalGridLines,
  AreaSeries
} from "react-vis";
import '../node_modules/react-vis/dist/style.css';

import GreatCircle from "great-circle";

export default function ElevationPlot(props) {
  let dist = 0;
  let data = [];
  if (props.trail == null) {
      return <span></span>;
  }
  const nodes = props.trail.nodes;
  let nonZero = false;
  for (let i = 0; i < nodes.length; i++) {
    data.push({ x: nodes[i].distance, y: nodes[i].elevation });
    if (nodes[i].elevation !== 0) {
        nonZero = true;
    }
  }
  if (!nonZero) {
      return <span></span>;
  }
  return (
    <FlexibleWidthXYPlot height={200}>
      <VerticalGridLines tickTotal={dist}/>
      <HorizontalGridLines />
      <XAxis tickTotal={props.trail.length}/>
      <YAxis />
      <AreaSeries
        className="area-series-example"
        curve="curveNatural"
        data={data}
      />
    </FlexibleWidthXYPlot>
  );
}

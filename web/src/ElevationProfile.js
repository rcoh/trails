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
  let prev;
  if (props.trail == null) {
      return <span></span>;
  }
  const nodes = props.trail.nodes;
  let nonZero = false;
  for (let i = 0; i < nodes.length; i++) {
    if (prev) {
      dist += GreatCircle.distance(
        prev.lat,
        prev.lon,
        nodes[i].lat,
        nodes[i].lon
      );
    }
    prev = nodes[i];
    data.push({ x: dist, y: nodes[i].elevation });
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
      <XAxis tickTotal={dist}/>
      <YAxis />
      <AreaSeries
        className="area-series-example"
        curve="curveNatural"
        data={data}
      />
    </FlexibleWidthXYPlot>
  );
}

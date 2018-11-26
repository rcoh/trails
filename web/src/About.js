import React, { Component } from "react";
import { Paragraph, Heading, Pane, Card } from "evergreen-ui";
import FindTrails from "./FindTrails";

export default class About extends Component {
  render() {
    const pSize = 500;
    return (
      <Pane display="flex" justifyContent="center">
        <Card background="tint1" padding="1em" maxWidth="800px">
          <Heading size={800} marginTop="default">
            About TrailsTo.Run
          </Heading>
          <Paragraph size={pSize} marginTop="default">
            Trails to run takes data from Open Street Map and uses it to build a
            database of running routes. This database can then be used to find
            running routes near you, filterable by distance and elevation gain.
            Currently, open street map data is indexed from the United States,
            British Columbia and the UK. I'm in the process of ingesting data
            globally.
          </Paragraph>
          <Paragraph size={pSize} marginTop="default">
            TrailsTo.Run is built and maintained by{" "}
            <a href="https://rcoh.me">Russell Cohen</a>. Give it a try, and let
            me know if you find some new trails (and also if you run into
            terrible data quality issues, I'm still working out some kinks)!
          </Paragraph>

          <Heading size={600} marginTop="default">
            FAQ
          </Heading>
          <Heading size={500} marginTop="default">
            How does it work?
          </Heading>

          <Paragraph size={pSize} marginTop="default">
            The raw data comes from <a href="https://openstreetmap.org">Open Street Map</a>, but there's a hefty amount
            of post processing to get it into a usuable form. When you query, I
            search for trailheads within a plausible drive time, then I filter
            loops from those trailheads.
          </Paragraph>

          <Heading size={500} marginTop="default">
            Isn't this just like AllTrails, Trail Running Project, etc.?
          </Heading>
          <Paragraph size={pSize} marginTop="default">
            It's similar, but because the loops are generated automatically, I
            have a lot more variation. Plus, a surprisingly large number of
            routes on Trail Running Project aren't loops, which just seems dumb.
          </Paragraph>
        </Card>
      </Pane>
    );
  }
}

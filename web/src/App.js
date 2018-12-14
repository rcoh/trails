import React, { Component } from "react";
import {
  BrowserRouter as Router,
  Route,
  Switch,
  Link,
  withRouter
} from "react-router-dom";
import { Pane, Text, Strong } from "evergreen-ui";
import FindTrails from "./FindTrails";
import About from "./About";
import Explore from "./Explore";
import ReactGA from 'react-ga';

const IndexComponent = () => <FindTrails />;
const AboutComponent = () => <About />;
const ExploreComponent = () => <Explore />;
const Users = () => <h2>Users</h2>;

if (process.env["NODE_ENV"] === "production") {
  ReactGA.initialize('UA-111671237-2', {debug: false});
}

class AppRouter extends Component {
  render() {
    return (
      <Router>
        <div>
          <RoutedNavBar />
          <div key="content" className="content">
            <Switch>
              <Route path="/" exact component={IndexComponent} />
              <Route path="/search" component={IndexComponent} />
              <Route path="/explore" component={ExploreComponent} />
              <Route path="/about" component={AboutComponent} />
              <Route component={Users} />
            </Switch>
          </div>
        </div>
      </Router>
    );
  }
}

class NavBar extends Component {
  render() {
    const navigation = [
      { url: "/search", text: "Search" },
      { url: "/explore", text: "Explore"},
      { url: "/about", text: "About" },
    ];
    ReactGA.pageview(this.props.location.pathname);
    const links = navigation.map(nav => {
      const active = nav.url === this.props.location.pathname || (nav.url === "/search" && this.props.location.pathname === "/");
      if (active) {
        return (
          <Link key={nav.url} to={nav.url} className="nav-item">
            <Strong>{nav.text}</Strong>
          </Link>
        );
      } else {
        return (
          <Link key={nav.url} to={nav.url} className="nav-item">
            <Text>{nav.text}</Text>
          </Link>
        );
      }
    });
    return (
      <Pane
        location={this.props.location}
        marginLeft="-10px"
        marginTop="-10px"
        marginRight="-8px"
        background="blueTint"
        display="flex"
        alignItems="center"
        flexWrap="wrap"
      >
        {links}
        <a className="nav-item" href="https://ko-fi.com/Q5Q6MIB5"><Text>Support TrailsTo.Run</Text></a>
      </Pane>
    );
  }
}

const RoutedNavBar = withRouter(NavBar);
export default AppRouter;

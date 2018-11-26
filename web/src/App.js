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

const IndexComponent = () => <FindTrails />;
const AboutComponent = () => <About />;
const Users = () => <h2>Users</h2>;

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
      { url: "/about", text: "About" },
    ];
    const links = navigation.map(nav => {
      const active = nav.url === this.props.location.pathname || nav.url === "/search" && this.props.location.pathname === "/";
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
        height="40px"
        marginLeft="-10px"
        marginTop="-10px"
        marginRight="-10px"
        background="blueTint"
        display="flex"
        alignItems="center"
      >
        {links}
        <a className="nav-item" href="https://ko-fi.com/Q5Q6MIB5"><Text>Support TrailsTo.Run</Text></a>
      </Pane>
    );
  }
}

const RoutedNavBar = withRouter(NavBar);
export default AppRouter;

import  React, { Component } from "react";
import {
  BrowserRouter as Router,
  Route,
  Switch,
  NavLink,
  withRouter
} from "react-router-dom";
import { Pane } from "evergreen-ui";
import FindTrails from "./FindTrails";

const Blerp = () => <h2>Hello</h2>;
const Index = () => <FindTrails />;
const About = () => <h2>About</h2>;
const Users = () => <h2>Users</h2>;

class AppRouter extends Component {
  render() {
    return <Router>
      <div>
        <div key="nav" class="nav">
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/explore">Explore</NavLink>
        </div >
        <div key="content">
          <Switch>
            <Route path="/" exact component={Index} />
            <Route path="/search" component={Index} />
            <Route path="/explore" component={About} />
            <Route component={Users} />
          </Switch>
        </div>
      </div>
    </Router>;
  }
}

export default AppRouter;

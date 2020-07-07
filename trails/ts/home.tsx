import mapboxgl from "mapbox-gl";
import MapboxGeocoder from "mapbox-gl-geocoder";
import React from "react";
import ReactDOM from "react-dom";
import { InfoPanel } from "./panel";
import { api, downloadNetwork } from "./api";
mapboxgl.accessToken =
  "pk.eyJ1IjoiZXZlcnlzaW5nbGV0cmFpbCIsImEiOiJja2JsNmV2YjcwaWY5MnFxbmdtanF4aGUyIn0.ioFGm3P5s1kOpv7fJerp7g";

const removePath = (map: mapboxgl.Map, networkId: string) => {
  const mapId = `circuit-${networkId}`;
  map.removeLayer(mapId);
  map.removeSource(mapId);
};

const loadVisibleParks = async (map: mapboxgl.Map) => {
  let hoveredParkId: string | number;
  const bounds = map.getBounds();
  const visibleAreas = await api("/api/areas", "POST", {
    sw: bounds.getSouthWest(),
    ne: bounds.getNorthEast(),
  });
  const { data } = await visibleAreas.json();
  if (map.getSource("parks") !== undefined) {
    const source = map.getSource("parks");
    if (source.type == "geojson") {
      source.setData(data);
    } else {
      throw new Error("unexpected source");
    }
    return;
  }

  // TODO: refactor to split new data from initialization
  map.addSource("parks", {
    type: "geojson",
    data,
  });
  map.addLayer({
    id: "parks-layer",
    type: "fill",
    source: "parks",
    paint: {
      "fill-color": ["get", "fill_color"],
      "fill-opacity": [
        "case",
        ["boolean", ["feature-state", "focused"], false],
        0.0,
        ["boolean", ["feature-state", "hover"], false],
        0.05,
        0.3,
      ],
    },
  });
  map.addLayer({
    id: "parks-outlines",
    type: "line",
    source: "parks",
    paint: {
      "line-color": "#333333",
      "line-width": 3,
      "line-opacity": 0.7,
    },
  });

  map.on("mouseenter", "parks-layer", function (e) {
    map.getCanvas().style.cursor = "pointer";
  });
  map.on("mousemove", "parks-layer", function (e) {
    if (e.features.length > 0) {
      if (hoveredParkId != null) {
        map.setFeatureState(
          { source: "parks", id: hoveredParkId },
          { hover: false }
        );
      }
      hoveredParkId = e.features[0].id;
      map.setFeatureState(
        { source: "parks", id: hoveredParkId },
        { hover: true }
      );
    }
  });

  // Change it back to a pointer when it leaves.
  map.on("mouseleave", "parks-layer", function () {
    map.getCanvas().style.cursor = "";
    if (hoveredParkId != null) {
      map.setFeatureState(
        { source: "parks", id: hoveredParkId },
        { hover: false }
      );
    }
    hoveredParkId = null;
  });

  map.on("click", "parks-layer", async function (e) {
    const park = e.features[0];
    map.setFeatureState({ source: "parks", id: park.id }, { focused: true });
    /*new mapboxgl.Popup()
      .setLngLat(JSON.parse(park.properties.center))
      .setHTML(await (await downloadNetwork(park.properties.id)).html)
      .addTo(map);*/

    const domContainer = document.getElementById("info-panel");
    ReactDOM.render(
      <InfoPanel
        mapboxId={park.id}
        networkId={park.properties.id}
        map={map}
        bb={JSON.parse(park.properties.bb)}
      />,
      domContainer
    );
  });
};

export const getCookie = (name: string) => {
  var cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};
const setupMap = async (center: any, perimeter: any) => {
  const map = new mapboxgl.Map({
    container: "map",
    style: "mapbox://styles/mapbox/outdoors-v11",
    center: center,
    zoom: 11,
  });
  map.addControl(
    new MapboxGeocoder({
      accessToken: mapboxgl.accessToken,
      zoom: 14,
      //placeholder: 'Enter search e.g. Lincoln Park',
      mapboxgl: mapboxgl,
    })
  );
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }));
  map.addControl(
    new mapboxgl.GeolocateControl({
      positionOptions: {
        enableHighAccuracy: true,
      },
      trackUserLocation: true,
    })
  );
  map.on("load", async () => await loadVisibleParks(map));
  map.on("moveend", () => {
    console.log("reloading parks");
    loadVisibleParks(map);
  });

  return map;
};
(async () => {
  const resp = await (await fetch("/api/default")).json();
  const { center } = resp;
  await setupMap(center, []);
})();

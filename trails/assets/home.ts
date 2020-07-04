import mapboxgl, { GeoJSONSource } from "mapbox-gl";
import { Feature, FeatureCollection } from "geojson";
import MapboxGeocoder from "mapbox-gl-geocoder";
mapboxgl.accessToken =
  "pk.eyJ1IjoiZXZlcnlzaW5nbGV0cmFpbCIsImEiOiJja2JsNmV2YjcwaWY5MnFxbmdtanF4aGUyIn0.ioFGm3P5s1kOpv7fJerp7g";

let parks: Feature[] = [];

interface NetworkResp {
  html: string;
}

export const computeGpx = async (networkId: string): Promise<NetworkResp> => {
  return await (await api(`/api/circuit/${networkId}/`, "POST")).json();
};

const downloadNetwork = async (networkId: string): Promise<NetworkResp> => {
  return await (await api(`/api/network/${networkId}/`, "GET")).json();
};

const api = async (url: string, method: "GET" | "POST", data?: any) => {
  let body = undefined;
  if (data != null) {
    body = JSON.stringify(data);
  }
  let args = {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body,
  };
  return fetch(url, args);
};

const loadVisibleParks = async (map: mapboxgl.Map) => {
  let hoveredParkId: string | number;
  const bounds = map.getBounds();
  const visibleAreas = await api("/api/areas", "POST", {
    sw: bounds.getSouthWest(),
    ne: bounds.getNorthEast(),
  });
  const { data: newData } = await visibleAreas.json();
  const parksInData = newData.features.map((feat: Feature) => feat.id);
  const parkSet = new Set(parksInData);
  const parkIdsLoaded = new Set(parks.map((park) => park.id));
  const parksAlreadyLoaded = parks.filter((park) => !parkSet.has(park.id));
  if (parksInData.every((parkId: number) => parkIdsLoaded.has(parkId))) {
    // we've already loaded all the parks for this region
    return;
  }
  newData.features.push(...parksAlreadyLoaded);
  parks = newData.features;

  if (map.getSource("parks") !== undefined) {
    const source = map.getSource("parks");
    if (source.type == "geojson") {
      source.setData(newData);
    } else {
      throw new Error("unexpected source");
    }
    return;
  }

  // TODO: refactor to split new data from initialization
  map.addSource("parks", {
    type: "geojson",
    data: newData,
  });
  map.addLayer({
    id: "parks-layer",
    type: "fill",
    source: "parks",
    paint: {
      "fill-color": ["get", "fill_color"],
      "fill-opacity": [
        "case",
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

  map.on("click", "parks-layer", function (e) {
    const park = e.features[0];
    const coordinates = park.properties.center;
    const description = park.properties.description;

    const popup = new mapboxgl.Popup()
      .setLngLat(JSON.parse(coordinates))
      .addTo(map);

    // TODO: react would be useful...
    const setHtml = (html: string) => {
      popup.setHTML(html);
      const zoomLink = document.getElementById(`${park.properties.id}-zoom`);
      zoomLink.onclick = () => {
        map.fitBounds(JSON.parse(park.properties.bb));
      };
      if (park.properties.circuit_status == "undone") {
        const el = document.getElementById(park.properties.id);
        if (el != null) {
          el.onclick = async () => {
            const resp = await computeGpx(park.properties.id);
            setHtml(resp.html);
          };
        }
      }
    };
    setHtml(description);
    //popup.addTo(map);

    const refresh = setInterval(async () => {
      const resp = await downloadNetwork(park.properties.id);
      setHtml(resp.html);
    }, 5000);

    popup.on("close", () => {
      clearInterval(refresh);
    });
  });
};

const getCookie = (name: string) => {
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
    loadVisibleParks(map);
  });

  return map;
};
(async () => {
  const resp = await (await fetch("/api/default")).json();
  const { center } = resp;
  await setupMap(center, []);
})();

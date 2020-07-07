import React, { useEffect, useState, useRef } from "react";
import {
  NetworkResp,
  downloadPath,
  downloadNetwork,
  Circuit,
  computeGpx,
} from "./api";
interface InfoPanelProps {
  networkId: string;
  mapboxId: number | string;
  map: mapboxgl.Map;
  bb: any;
}

const circuitInfo = (
  circuit: Circuit | null,
  computeCircuit: () => void,
  map: mapboxgl.Map,
  networkId: string
) => {
  if (circuit == null) {
    return (
      <button
        type="button"
        className="btn btn-primary btn-sm"
        onClick={computeCircuit}
      >
        Calculate Tour
      </button>
    );
    //return <a onClick={computeCircuit}>Compute complete tour</a>;
  }
  if (circuit.status == "complete") {
    return (
      <div className="info-row">
        <span>Full tour: {circuit.total_length} miles</span>
        <a href={circuit.download_url}>Download GPX</a>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => showPath(map, circuit.id, networkId)}
        >
          Show Route
        </button>
      </div>
    );
  } else if (circuit.status == "in_progress") {
    return <div>Calcuating tour...({circuit.since})</div>;
  } else {
    return (
      <div>
        Circuit failed to be built. Please{" "}
        <a href="https://github.com/rcoh/trails/issues">
          file an issue on GitHub
        </a>
        .
      </div>
    );
  }
};

function usePrevious(value: any) {
  const ref = useRef();
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}

export const InfoPanel = ({ networkId, bb, map, mapboxId }: InfoPanelProps) => {
  const [polling, setPolling] = useState(false);
  const [poll, setPoll] = useState(0);
  const [closed, setClosed] = useState(false);
  const [network, setData] = useState<NetworkResp | undefined>(undefined);
  const previousMapboxId = usePrevious(mapboxId);
  useEffect(() => {
    console.log("downlaod effect");
    const internal = async () => {
      console.log("downloading network", poll);
      const network = await downloadNetwork(networkId);
      if (network.circuit && network.circuit.status != "in_progress") {
        setPolling(false);
      }
      setData(network);
    };
    internal();
  }, [networkId, poll]);

  // If the networkId changes, stop polling
  useEffect(() => {
    setPolling(false);
    if (previousMapboxId != null) {
      map.setFeatureState(
        { source: "parks", id: previousMapboxId },
        { focused: false }
      );
    }
    setClosed(false);
  }, [networkId]);

  useEffect(() => {
    console.log("starting effect...", polling);
    let timer: number = null;
    const callback = () => {
      if (polling) {
        setPoll((poll) => poll + 1);
        timer = setTimeout(() => {
          console.log("backoff to 1 second");
          callback();
        }, 1000);
      }
    };
    timer = setTimeout(() => {
      callback();
    }, 100);
    return () => {
      console.log("cleared timer");
      clearTimeout(timer);
    };
  }, [polling]);

  function zoom() {
    map.fitBounds(bb);
  }

  async function computeCircuit() {
    const data = await computeGpx(networkId);
    setData(data);
    setPolling(true);
  }
  if (closed) {
    return <span></span>;
  }
  if (network == null) {
    return <div className="info-panel">Loading...</div>;
  } else {
    return (
      <div className="info-panel">
        <div className="info-header">
          <h4>{network.name}</h4>
          <button
            type="button"
            className="close"
            aria-label="Close"
            onClick={() => setClosed(true)}
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div>
          <div className="info-row">
            <span>{network.milage} miles of trails</span>
            <button
              onClick={zoom}
              type="button"
              className="btn btn-primary btn-sm"
            >
              Zoom
            </button>
          </div>
          <hr className="d-none d-md-block" />
          {circuitInfo(network.circuit, computeCircuit, map, networkId)}
        </div>
      </div>
    );
  }
};

const showPath = async (
  map: mapboxgl.Map,
  circuitId: string,
  networkId: string
) => {
  const { json } = await downloadPath(circuitId);
  const mapId = `circuit-${networkId}`;

  map.addSource(mapId, { type: "geojson", data: json });
  map.addLayer({
    id: mapId,
    type: "line",
    source: mapId,
    paint: {
      "line-color": "black",
      "line-width": 1,
      "line-opacity": 1,
    },
  });
};

// TODO: react would be useful...
/*const setHtml = (resp: NetworkResp) => {
      const { html } = resp;
      popup.setHTML(html);
      const zoomLink = document.getElementById(`${park.properties.id}-zoom`);
      zoomLink.onclick = () => {
        map.fitBounds(JSON.parse(park.properties.bb));
      };
      const el = document.getElementById(park.properties.id);
      if (el != null) {
        el.onclick = async () => {
          const resp = await computeGpx(park.properties.id);
          setHtml(resp);
        };
      }

      const showOnMap = document.getElementById(`${park.properties.id}-show`);
      if (showOnMap != null) {
        showOnMap.onclick = () => {
          if (resp.circuit) {
            showPath(map, resp.circuit.id, park.properties.id);

          }
        };
      }
    };
    const network = await downloadNetwork(park.properties.id);
    setHtml(network);
    const sourceId = `trailheads-${park.properties.id}`;
    if (map.getSource(sourceId) == null) {
      map.addSource(sourceId, {
        type: "geojson",
        data: network.trailheads,
      });
      map.addLayer({
        id: sourceId,
        type: "symbol",
        source: sourceId,
        layout: {
          "icon-image": "car-11",
          "icon-allow-overlap": true,
        },
      });
    }

    const refresh = setInterval(async () => {
      try {
        const resp = await downloadNetwork(park.properties.id);
        setHtml(resp);
      } catch (err) {
        clearInterval(refresh);
        alert("Something went wrong, please refresh the page");
      }
    }, 5000);

    popup.on("close", () => {
      console.log(`setting ${park.id} to unfocused`);
      map.setFeatureState({ source: "parks", id: park.id }, { focused: false });
      //removePath(map, park.properties.id);
      clearInterval(refresh);
    });
  });*/

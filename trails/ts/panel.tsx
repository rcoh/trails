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

function useInterval(callback: () => void, delay: number) {
  const savedCallback = useRef<() => void>();

  // Remember the latest callback.
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval.
  useEffect(() => {
    function tick() {
      savedCallback.current();
    }
    if (delay !== null) {
      let id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
}

interface PollConfig {
  polls: number;
}

export const InfoPanel = ({ networkId, bb, map, mapboxId }: InfoPanelProps) => {
  const [trailHeadsVisible, setTrailheadsVisible] = useState(false);
  const [polling, setPolling] = useState<PollConfig | undefined>(undefined);
  const [closed, setClosed] = useState(false);
  const [network, setData] = useState<NetworkResp | undefined>(undefined);
  const previousMapboxId = usePrevious(mapboxId);
  useEffect(() => {
    const internal = async () => {
      const network = await downloadNetwork(networkId);
      if (network.circuit == null || network.circuit.status != "in_progress") {
        setPolling(undefined);
      } else if (polling == undefined) {
        setPolling({polls: 1});
      }
      setData(network);
    };
    internal();
  }, [networkId, polling]);

  // If the networkId changes, stop polling
  useEffect(() => {
    setPolling(undefined);
    if (previousMapboxId != null) {
      map.setFeatureState(
        { source: "parks", id: previousMapboxId },
        { focused: false }
      );
    }
    setClosed(false);
    setTrailheadsVisible(false);
  }, [networkId]);

  useInterval(
    () => {
      setPolling((polling) => {
        if (polling != undefined) {
          return { polls : polling.polls + 1}
        } else {
          return undefined;
        }
      });
    },
    polling != null ? Math.min(10000, polling.polls * 500) : null
  );

  function zoom() {
    map.fitBounds(bb);
  }

  function toggleTrailHeads() {
    setTrailheadsVisible((visible) => !visible);
  }

  useEffect(() => {
    if (network == null) {
      return;
    }
    const sourceId = `trailheads`;
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
    } else {
      const source = map.getSource(sourceId);
      if (source.type == "geojson") {
        source.setData(network.trailheads);
      }
    }
    if (trailHeadsVisible) {
      map.setLayoutProperty(sourceId, "visibility", "visible");
    } else {
      map.setLayoutProperty(sourceId, "visibility", "none");
    }
  }, [trailHeadsVisible, network]);

  async function computeCircuit() {
    await computeGpx(networkId);
    setPolling({polls: 1});
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
          <h4>{network.name || "Unnamed Area"}</h4>
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
              onClick={toggleTrailHeads}
              type="button"
              className="btn btn-primary btn-sm"
            >
              {trailHeadsVisible ? "Hide" : "Show"}{" "}
              {network.trailheads.features.length} trailheads
            </button>
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

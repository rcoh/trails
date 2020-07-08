import { FeatureCollection } from "geojson";
import { getCookie } from "./home";

interface CircuitBase {
  id: string;
  status: string;
}

interface CompleteCircuit extends CircuitBase {
  status: "complete";
  total_length: string;
  download_url: string;
}

interface InProgressCircuit extends CircuitBase {
  status: "in_progress";
  since: string;
}

interface ErrorCircuit extends CircuitBase {
  status: "error";
  error: string;
}

export type Circuit = CompleteCircuit | InProgressCircuit | ErrorCircuit;

export interface NetworkResp {
  html: string;
  name: string;
  milage: string;
  circuit: Circuit | null;
  trailheads: FeatureCollection;
}
interface CircuitResponse {
  json: string;
}

interface ComputeGpxResponse {
    circuit_id: string;
}

export const computeGpx = async (networkId: string): Promise<ComputeGpxResponse> => {
  return await (await api(`/api/circuit/${networkId}/`, "POST")).json();
};
export const downloadPath = async (
  circuitId: string
): Promise<CircuitResponse> => {
  return await (await api(`/api/circuit/${circuitId}/json`, "GET")).json();
};
export const downloadNetwork = async (
  networkId: string
): Promise<NetworkResp> => {
  return await (await api(`/api/network/${networkId}/`, "GET")).json();
};
export const api = async (url: string, method: "GET" | "POST", data?: any) => {
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

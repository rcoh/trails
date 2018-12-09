export const server = process.env["REACT_APP_SERVER"] || "http://localhost:8000";

export const loadAPI = async (endpoint, data) => {
  const resp = await fetch(`${server}/api/${endpoint}`, {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json"
    }
  });
  if (!resp.ok) {
    throw Error(JSON.stringify(await resp.json()));
  }
  return await resp.json();
};

export const nearbyTrailheads = async ({location, max_travel_time_minutes, units}) => {
  return loadAPI("trailheads/", {units, location_filter: {lat: location.lat, lon: location.lng, max_travel_time_minutes}});
}
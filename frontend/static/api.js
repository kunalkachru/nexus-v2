export async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function loadMetrics() {
  return fetchJson("/api/metrics");
}

export function loadIncident(incidentId) {
  return fetchJson(`/run-incident?incident_id=${encodeURIComponent(incidentId)}`);
}

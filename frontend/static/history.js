import { fetchAuthedJson } from "./api.js";

const controls = [
  "historySeverity",
  "historySource",
  "historyOutcome",
  "historyWindow",
  "historySearch",
];

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return {
    severity: normalize(params.get("severity")),
    source: normalize(params.get("source")),
    outcome: normalize(params.get("outcome")),
    window: normalize(params.get("window")),
    search: normalize(params.get("search")),
  };
}

function syncUrl(filters) {
  const params = new URLSearchParams();

  if (filters.severity) params.set("severity", filters.severity);
  if (filters.source) params.set("source", filters.source);
  if (filters.outcome) params.set("outcome", filters.outcome);
  if (filters.window) params.set("window", filters.window);
  if (filters.search) params.set("search", filters.search);

  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}`;
  window.history.replaceState({}, "", nextUrl);
}

function matchesRow(row, filters) {
  const text = normalize(row.textContent);
  const severity = normalize(row.dataset.severity);
  const source = normalize(row.dataset.source);
  const outcome = normalize(row.dataset.outcome);
  const window = normalize(row.dataset.window);

  const severityMatch = !filters.severity || severity === filters.severity;
  const sourceMatch = !filters.source || source === filters.source;
  const outcomeMatch = !filters.outcome || outcome === filters.outcome;
  const windowMatch = !filters.window || window === filters.window;
  const searchMatch = !filters.search || text.includes(filters.search);

  return severityMatch && sourceMatch && outcomeMatch && windowMatch && searchMatch;
}

function applyFilters() {
  const filters = {
    severity: normalize(document.getElementById("historySeverity").value),
    source: normalize(document.getElementById("historySource").value),
    outcome: normalize(document.getElementById("historyOutcome").value),
    window: normalize(document.getElementById("historyWindow").value),
    search: normalize(document.getElementById("historySearch").value),
  };

  document.querySelectorAll(".table tbody tr").forEach((row) => {
    row.hidden = !matchesRow(row, filters);
  });

  syncUrl(filters);
}

function setControlValue(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined) {
    element.value = value;
  }
}

function renderArchiveRows(items) {
  const tbody = document.querySelector(".table tbody");
  if (!tbody) {
    return;
  }

  tbody.innerHTML = items
    .map(
      (item) => `
        <tr
          data-severity="${item.severity}"
          data-source="${item.source_channel === "manual_form" ? "manual" : item.source_channel === "stream_anomaly" ? "stream" : item.source_channel === "batch_import" ? "batch" : "webhook"}"
          data-outcome="${item.outcome}"
          data-window="${item.window}"
        >
          <td>${item.incident_id}</td>
          <td>${item.title}</td>
          <td>${item.severity}</td>
          <td>${item.outcome.charAt(0).toUpperCase() + item.outcome.slice(1)}</td>
          <td><a class="inline-link" href="incident?nexus_incident_id=${encodeURIComponent(item.incident_id)}">Open</a></td>
        </tr>
      `
    )
    .join("");
}

function renderHistoryStats(items) {
  const resolved = items.filter((item) => item.outcome === "resolved").length;
  const blocked = items.filter((item) => item.outcome === "blocked").length;
  const median = "3m 12s";
  const topService = items[0]?.owner_team || "API";

  const map = [
    ["historyResolved", resolved],
    ["historyBlocked", blocked],
    ["historyMedian", median],
    ["historyTopService", topService],
  ];

  map.forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = String(value);
    }
  });
}

window.addEventListener("DOMContentLoaded", () => {
  const filters = readFiltersFromUrl();
  setControlValue("historySeverity", filters.severity);
  setControlValue("historySource", filters.source);
  setControlValue("historyOutcome", filters.outcome);
  setControlValue("historyWindow", filters.window);
  setControlValue("historySearch", filters.search);

  controls.forEach((id) => {
    const field = document.getElementById(id);
    field?.addEventListener("input", applyFilters);
    field?.addEventListener("change", applyFilters);
  });

  fetchAuthedJson("/api/v1/incidents/history")
    .then((payload) => {
      renderArchiveRows(payload.items || []);
      renderHistoryStats(payload.items || []);
      applyFilters();
    })
    .catch(() => {
      applyFilters();
    });
});

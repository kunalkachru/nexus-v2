const THEME_STORAGE_KEY = "nexus.theme";
const ROUTE_LABELS = {
  "/": "Command Center",
  "/queue": "Command Center",
  "/dashboard": "Command Center",
  "/incident": "Incident Detail",
  "/inputs": "Input Channels",
  "/history": "History",
  "/replay": "Replay",
  "/training": "Learning & Controls",
  "/settings": "Settings",
};

function isInternalRoute(pathname) {
  return Object.hasOwn(ROUTE_LABELS, pathname);
}

function currentRoute() {
  const url = new URL(window.location.href);
  url.searchParams.delete("return_to");
  return `${url.pathname}${url.search}${url.hash}`;
}

function normalizeInternalTarget(target) {
  if (!target) {
    return null;
  }

  try {
    const url = new URL(target, window.location.origin);
    if (url.origin !== window.location.origin || !isInternalRoute(url.pathname)) {
      return null;
    }
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return null;
  }
}

function routeLabel(target) {
  const normalized = normalizeInternalTarget(target);
  if (!normalized) {
    return "previous screen";
  }

  const url = new URL(normalized, window.location.origin);
  return ROUTE_LABELS[url.pathname] || "previous screen";
}

function withReturnTo(target) {
  const normalized = normalizeInternalTarget(target);
  if (!normalized) {
    return target;
  }

  const url = new URL(normalized, window.location.origin);
  if (!url.searchParams.has("return_to")) {
    url.searchParams.set("return_to", currentRoute());
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

function getReturnTarget() {
  const params = new URLSearchParams(window.location.search);
  const explicit = normalizeInternalTarget(params.get("return_to"));
  if (explicit) {
    return explicit;
  }

  if (!document.referrer) {
    return null;
  }

  return normalizeInternalTarget(document.referrer);
}

function applyContextLinks(root = document) {
  root.querySelectorAll("[data-preserve-return]").forEach((link) => {
    const href = link.getAttribute("href");
    if (href) {
      link.setAttribute("href", withReturnTo(href));
    }
  });

  const returnTarget = getReturnTarget();
  root.querySelectorAll("[data-context-back-link]").forEach((link) => {
    const fallbackHref = link.dataset.fallbackHref || "/queue";
    const fallbackLabel = link.dataset.fallbackLabel || `Back to ${routeLabel(fallbackHref)}`;
    const href = returnTarget || normalizeInternalTarget(fallbackHref) || "/queue";
    link.setAttribute("href", href);
    link.textContent = returnTarget ? `Back to ${routeLabel(returnTarget)}` : fallbackLabel;
  });
}

function getPreferredTheme() {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
  } catch {
    // Ignore storage access failures and fall back to system preference.
  }

  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore storage access failures.
  }
}

function createThemeToggle(initialTheme) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "nav-link theme-toggle";

  const syncLabel = () => {
    const isLight = document.documentElement.dataset.theme === "light";
    button.textContent = `Theme · ${isLight ? "Light" : "Dark"}`;
    button.setAttribute("aria-label", `Switch to ${isLight ? "dark" : "light"} mode`);
    button.setAttribute("aria-pressed", String(isLight));
  };

  setTheme(initialTheme);
  syncLabel();

  button.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    syncLabel();
  });

  return button;
}

window.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".app-nav");
  window.NexusNavigation = { applyContextLinks, getReturnTarget, routeLabel, withReturnTo };

  if (!nav || nav.querySelector(".theme-toggle")) {
    applyContextLinks();
    return;
  }

  nav.appendChild(createThemeToggle(getPreferredTheme()));
  applyContextLinks();
});

const THEME_STORAGE_KEY = "nexus.theme";
const PREFETCHED_ROUTES = new Set();
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

function ensureRouteTransitionOverlay() {
  let overlay = document.getElementById("routeTransitionOverlay");
  if (overlay) {
    return overlay;
  }

  overlay = document.createElement("div");
  overlay.id = "routeTransitionOverlay";
  overlay.className = "route-transition-overlay";
  overlay.setAttribute("aria-hidden", "true");
  overlay.innerHTML = `
    <div class="route-transition-card" role="status" aria-live="polite">
      <div class="route-transition-spinner" aria-hidden="true"></div>
      <div class="route-transition-copy">
        <div class="route-transition-label" id="routeTransitionLabel">Opening workspace...</div>
        <div class="route-transition-note">Warming the next screen and preserving your current context.</div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  return overlay;
}

function endRouteTransition() {
  document.body.classList.remove("route-pending");
  const overlay = document.getElementById("routeTransitionOverlay");
  if (overlay) {
    overlay.classList.remove("is-visible");
    overlay.setAttribute("aria-hidden", "true");
  }
}

function beginRouteTransition(label = "Opening workspace...") {
  const overlay = ensureRouteTransitionOverlay();
  const labelNode = document.getElementById("routeTransitionLabel");
  if (labelNode) {
    labelNode.textContent = label;
  }
  document.body.classList.add("route-pending");
  overlay.classList.add("is-visible");
  overlay.setAttribute("aria-hidden", "false");
}

async function prefetchInternalTarget(target) {
  const normalized = normalizeInternalTarget(target);
  if (!normalized || PREFETCHED_ROUTES.has(normalized)) {
    return;
  }
  PREFETCHED_ROUTES.add(normalized);

  try {
    await fetch(normalized, {
      method: "GET",
      credentials: "same-origin",
    });
  } catch {
    // Ignore prefetch failures; navigation still works normally.
  }
}

function enhanceInternalLinks(root = document) {
  root.querySelectorAll("a[href]").forEach((link) => {
    const href = normalizeInternalTarget(link.getAttribute("href"));
    if (!href) {
      return;
    }

    if (!link.dataset.prefetchBound) {
      const warm = () => {
        prefetchInternalTarget(link.getAttribute("href"));
      };
      link.addEventListener("mouseenter", warm, { passive: true });
      link.addEventListener("focus", warm, { passive: true });
      link.addEventListener("touchstart", warm, { passive: true, once: true });
      link.dataset.prefetchBound = "1";
    }

    if (!link.dataset.transitionBound) {
      link.addEventListener("click", (event) => {
        if (event.defaultPrevented || event.button !== 0 || link.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
          return;
        }
        const target = normalizeInternalTarget(link.href || link.getAttribute("href"));
        if (!target) {
          return;
        }
        const label = link.dataset.loadingLabel || `Opening ${routeLabel(target)}...`;
        beginRouteTransition(label);
      });
      link.dataset.transitionBound = "1";
    }
  });
}

function scheduleRoutePrefetch(root = document) {
  const targets = Array.from(root.querySelectorAll("a[href]"))
    .map((link) => link.getAttribute("href"))
    .filter(Boolean)
    .filter((href, index, list) => list.indexOf(href) === index)
    .filter((href) => normalizeInternalTarget(href));

  const run = () => {
    targets.slice(0, 10).forEach((target) => {
      prefetchInternalTarget(target);
    });
  };

  if ("requestIdleCallback" in window) {
    window.requestIdleCallback(run, { timeout: 1200 });
  } else {
    window.setTimeout(run, 250);
  }
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
  window.NexusNavigation = { applyContextLinks, beginRouteTransition, endRouteTransition, getReturnTarget, routeLabel, withReturnTo };

  if (!nav || nav.querySelector(".theme-toggle")) {
    applyContextLinks();
    ensureRouteTransitionOverlay();
    enhanceInternalLinks();
    scheduleRoutePrefetch();
    return;
  }

  nav.appendChild(createThemeToggle(getPreferredTheme()));
  applyContextLinks();
  ensureRouteTransitionOverlay();
  enhanceInternalLinks();
  scheduleRoutePrefetch();
});

window.addEventListener("pageshow", () => {
  endRouteTransition();
});

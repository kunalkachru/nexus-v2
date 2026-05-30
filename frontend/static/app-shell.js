const THEME_STORAGE_KEY = "nexus.theme";

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
  if (!nav || nav.querySelector(".theme-toggle")) {
    return;
  }

  nav.appendChild(createThemeToggle(getPreferredTheme()));
});

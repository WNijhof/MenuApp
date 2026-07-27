export const DEFAULT_BACKGROUND_COLOR = "#f7f6f3";
export const DEFAULT_ACCENT_COLOR = "#c1440e";

function clamp(value) {
  return Math.min(255, Math.max(0, value));
}

// Derives the hover shade from a single accent color pick, mirroring how
// --accent-hover in styles.css is just a darker/lighter variant of --accent.
function shade(hex, percent) {
  const num = parseInt(hex.slice(1), 16);
  const amount = Math.round(2.55 * percent);
  const r = clamp((num >> 16) + amount);
  const g = clamp(((num >> 8) & 0x00ff) + amount);
  const b = clamp((num & 0x0000ff) + amount);
  return `#${(0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1)}`;
}

// Applied as inline styles on the root element so a custom pick wins over
// the light/dark `prefers-color-scheme` defaults in styles.css in both
// modes - once you've chosen colors, that's the theme, regardless of the
// visitor's OS setting.
export function applyTheme({ background_color, accent_color } = {}) {
  const root = document.documentElement.style;

  if (background_color) {
    root.setProperty("--bg", background_color);
  } else {
    root.removeProperty("--bg");
  }

  if (accent_color) {
    root.setProperty("--accent", accent_color);
    root.setProperty("--accent-hover", shade(accent_color, -18));
  } else {
    root.removeProperty("--accent");
    root.removeProperty("--accent-hover");
  }
}

/**
 * Deterministic colors for the Topics treemap (SpecialtyDomainsSection).
 *
 * Base hues are the validated 8-slot categorical palette (fixed order, never
 * cycled — see the dataviz skill). Reused for both the root Domain view and
 * each Domain's Field view: OpenAlex's Field→Domain mapping is many-to-one,
 * so a Field's local rank within its parent Domain (sorted by publication
 * volume) is already stable across the whole app — no global palette needed.
 * A Domain/Field beyond the 8th rank falls back to a neutral tone rather than
 * inventing a 9th "identity" hue; every cell carries its own direct label
 * (name + count) as the primary identification channel, so this is a
 * decorative distinction past that point, not a safety-critical one.
 *
 * Subfield/Topic levels (reached by drilling into a Field) are rendered as
 * lightness-shifted variants of that Field's own color, per the requested
 * "declinations of the Field's color" behaviour.
 */

const CATEGORICAL_PALETTE = [
  "#2a78d6", // blue
  "#eb6834", // orange
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#e87ba4", // magenta
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red
];

const OVERFLOW_COLOR = "#7c8a99"; // steel gray, for ranks beyond the 8-slot palette

function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  const d = max - min;
  if (d !== 0) {
    s = d / (1 - Math.abs(2 * l - 1));
    switch (max) {
      case r: h = ((g - b) / d) % 6; break;
      case g: h = (b - r) / d + 2; break;
      default: h = (r - g) / d + 4;
    }
    h *= 60;
    if (h < 0) h += 360;
  }
  return [h, s, l];
}

function hslToHex(h: number, s: number, l: number): string {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let [r, g, b] = [0, 0, 0];
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  const toHex = (v: number) =>
    Math.round((v + m) * 255).toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/** Color for a Domain or Field cell, by its 0-indexed rank among siblings
 * (sorted by publication volume descending). */
export function getCategoricalColor(rank: number): string {
  return rank < CATEGORICAL_PALETTE.length ? CATEGORICAL_PALETTE[rank] : OVERFLOW_COLOR;
}

/** A lightness-shifted variant of `baseHex`, spread evenly across `total`
 * siblings by `index` — used for Subfield/Topic cells within a drilled-into
 * Field, so they read as a family without being indistinguishable. */
export function getShade(baseHex: string, index: number, total: number): string {
  const [h, s] = hexToHsl(baseHex);
  const MIN_L = 0.32;
  const MAX_L = 0.72;
  const t = total <= 1 ? 0.5 : index / (total - 1);
  const l = MAX_L - t * (MAX_L - MIN_L);
  return hslToHex(h, Math.max(s, 0.35), l);
}

/** Legible ink color (near-black or white) for text drawn on top of `hex`. */
export function getContrastTextColor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return luminance > 0.42 ? "#111111" : "#ffffff";
}

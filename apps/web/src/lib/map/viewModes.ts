/**
 * Sensor view modes (G-14): colour treatments of the whole map, applied as
 * CSS/SVG filters on the map container, so switching never reloads data.
 *
 * - nvg: night-vision green, for night operations
 * - flir: thermal "ironbow" palette; bright features (fires, lit areas)
 *   read as hot
 * - crt: operations-console monitor look (scanlines, extra contrast)
 * - noir: high-contrast monochrome
 * - contrast: accessibility mode with stronger contrast and saturation
 */

export const VIEW_MODES = ["normal", "nvg", "flir", "crt", "noir", "contrast"] as const;
export type ViewMode = (typeof VIEW_MODES)[number];

export const isViewMode = (value: unknown): value is ViewMode =>
  typeof value === "string" && (VIEW_MODES as readonly string[]).includes(value);

/** SVG filter element ids used by modes that CSS filters cannot express */
export const FLIR_FILTER_ID = "phoenix-view-flir";

export function viewModeFilter(mode: ViewMode): string | undefined {
  switch (mode) {
    case "nvg":
      // Luminance -> green phosphor
      return "grayscale(1) brightness(1.15) contrast(1.25) sepia(1) hue-rotate(55deg) saturate(3.5)";
    case "flir":
      return `url(#${FLIR_FILTER_ID})`;
    case "crt":
      return "contrast(1.15) saturate(1.35) brightness(1.05)";
    case "noir":
      return "grayscale(1) contrast(1.6) brightness(0.95)";
    case "contrast":
      return "contrast(1.5) saturate(1.4) brightness(1.1)";
    default:
      return undefined;
  }
}

/**
 * Ironbow lookup (black -> purple -> red -> orange -> yellow -> white) as
 * feComponentTransfer tables, applied to luminance.
 */
export const IRONBOW = {
  r: "0 0.25 0.65 0.9 1 1",
  g: "0 0 0.1 0.45 0.85 1",
  b: "0 0.45 0.45 0.05 0.2 0.9",
};

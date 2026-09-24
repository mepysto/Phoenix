import { FLIR_FILTER_ID, IRONBOW } from "@/lib/map/viewModes";

/** Hidden SVG filter definitions referenced by the view modes (CSS `url(#id)`) */
export function ViewModeFilters() {
  return (
    <svg aria-hidden="true" width="0" height="0" style={{ position: "absolute" }}>
      <defs>
        <filter id={FLIR_FILTER_ID} colorInterpolationFilters="sRGB">
          {/* Luminance into every channel, then map it through the ironbow palette */}
          <feColorMatrix
            type="matrix"
            values="0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0 0 0 1 0"
          />
          <feComponentTransfer>
            <feFuncR type="table" tableValues={IRONBOW.r} />
            <feFuncG type="table" tableValues={IRONBOW.g} />
            <feFuncB type="table" tableValues={IRONBOW.b} />
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>
  );
}

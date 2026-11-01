interface PhoenixMarkProps {
  className?: string;
  title?: string;
}

/**
 * Phoenix logomark: the curve of the Earth with two wings rising from it.
 * Ember on the lower wing (the wound), regrowth on the upper (the repair).
 */
export function PhoenixMark({
  className = "h-7 w-7",
  title,
}: PhoenixMarkProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      fill="none"
    >
      {/* Horizon of the globe */}
      <path
        d="M4 24.5c3.2 2.6 7.4 4 12 4s8.8-1.4 12-4"
        stroke="currentColor"
        strokeOpacity="0.45"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* Lower wing */}
      <path
        d="M16 22.5c-2.2-3.4-6.4-5.2-11-4.6 2.4 3.3 6.6 5 11 4.6Z"
        fill="var(--ember, #ff6b3d)"
      />
      {/* Upper wing */}
      <path
        d="M16 22.5c.4-6.8 4.6-12.6 11-15-1 7.2-5.2 12.8-11 15Z"
        fill="var(--regrow, #34d0ac)"
      />
      {/* Body rising */}
      <path
        d="M16 22.5V9.5m0 0-2.6 2.6M16 9.5l2.6 2.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

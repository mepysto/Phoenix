import type { Config } from "tailwindcss";

/**
 * Phoenix palette. Two signal colours carry the mission:
 * ember marks damage and urgency, regrowth (primary) marks recovery and
 * action. Everything else is a cool "night orbit" grey so the two read.
 *
 * `gray` is overridden on purpose: the whole UI is built on gray-*, so the
 * retint applies everywhere at once. gray-500 is lifted to stay >= 4.5:1 on
 * gray-900/950 for small text.
 */
const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        gray: {
          50: "#F2F5FA",
          100: "#E3E9F2",
          200: "#C9D3E2",
          300: "#A6B4CA",
          400: "#8B9BB5",
          500: "#7889A6",
          600: "#44536E",
          700: "#2C3A52",
          800: "#1A2539",
          900: "#111A2B",
          950: "#0A111D",
        },
        primary: {
          50: "#E8FBF6",
          100: "#C6F5E8",
          200: "#93EBD5",
          300: "#5EDFC0",
          400: "#34D0AC",
          500: "#19B794",
          600: "#0B7D66",
          700: "#0E6556",
          800: "#0F5D4F",
          900: "#0E4C42",
        },
        ember: {
          300: "#FFB08F",
          400: "#FF8A5B",
          500: "#FF6B3D",
          600: "#E5501F",
          700: "#B23C15",
        },
        severity: {
          low: "#22c55e",
          medium: "#f59e0b",
          high: "#ef4444",
          critical: "#7c3aed",
        },
      },
      fontFamily: {
        sans: ["var(--font-sora)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      boxShadow: {
        // Elevation is a hairline first, a soft drop second
        panel: "0 0 0 1px rgb(44 58 82 / 0.7), 0 12px 32px -12px rgb(0 0 0 / 0.6)",
      },
      keyframes: {
        "ring-pulse": {
          "0%": { transform: "scale(0.6)", opacity: "0.9" },
          "100%": { transform: "scale(2.2)", opacity: "0" },
        },
        "panel-in": {
          "0%": { transform: "translateY(6px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
      animation: {
        "ring-pulse": "ring-pulse 1.8s cubic-bezier(0.2, 0.6, 0.3, 1) infinite",
        "panel-in": "panel-in 180ms cubic-bezier(0.2, 0.7, 0.3, 1) both",
      },
    },
  },
  plugins: [],
};

export default config;

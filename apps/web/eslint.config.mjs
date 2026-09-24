// ESLint 9 flat config. `next lint` is deprecated and, without a config,
// opened an interactive prompt (so lint never ran).
import { createRequire } from "node:module";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const require = createRequire(import.meta.url);
const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

// Shared legacy-format rules from packages/eslint-config
const sharedNextConfig = require("@phoenix/eslint-config/next.js");

const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "next-env.d.ts",
      "src/lib/api/schema.d.ts", // generated
      "public/cesium/**", // copied map runtimes (scripts/copy-map-assets.mjs)
      "public/maplibre/**",
      "coverage/**",
      "playwright-report/**",
      "test-results/**",
    ],
  },
  ...compat.config(sharedNextConfig),
];

export default config;

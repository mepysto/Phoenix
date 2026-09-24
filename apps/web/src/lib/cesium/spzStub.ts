/**
 * Stand-in for @spz-loader/core (Cesium's Gaussian-splat decoder), aliased in
 * next.config.ts. The real package inlines a WebAssembly binary as a string
 * that Next's production minifier rewrites into a template literal with an
 * invalid octal escape, which breaks the 3D engine's chunk ("Octal escape
 * sequences are not allowed in template strings"). Phoenix loads no SPZ
 * splats; tilesets without them are unaffected.
 */
export async function loadSpz(): Promise<never> {
  throw new Error("Gaussian splat (SPZ) content is not supported in this build");
}

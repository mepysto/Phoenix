import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the production Docker image
  output: "standalone",
  // Monorepo: trace workspace packages (@phoenix/shared) from the repo root
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  transpilePackages: ["@phoenix/shared"],
  experimental: {
    optimizePackageImports: ["lucide-react", "@phoenix/shared", "maplibre-gl"],
  },
  poweredByHeader: false,
  compress: true,
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
  },
  modularizeImports: {
    "lucide-react": {
      transform: "lucide-react/dist/esm/icons/{{kebabCase member}}",
      skipDefaultConversion: true,
    },
  },
  webpack: (config, { isServer }) => {
    // Cesium's SPZ (Gaussian splat) decoder inlines WebAssembly as a string the
    // minifier breaks; Phoenix does not use splats (see src/lib/cesium/spzStub.ts)
    config.resolve.alias = {
      ...config.resolve.alias,
      "@spz-loader/core": path.join(process.cwd(), "src/lib/cesium/spzStub.ts"),
    };
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization?.splitChunks,
          cacheGroups: {
            ...(
              config.optimization?.splitChunks as {
                cacheGroups?: Record<string, unknown>;
              }
            )?.cacheGroups,
            mapLibraries: {
              test: /[\\/]node_modules[\\/](maplibre-gl)[\\/]/,
              name: "map-libraries",
              priority: 10,
              reuseExistingChunk: true,
            },
          },
        },
      };
    }
    return config;
  },
};

export default nextConfig;

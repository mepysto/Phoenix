import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Phoenix — Humanitarian Digital Twin",
    short_name: "Phoenix",
    description:
      "Live disasters, where help is needed, and how to plan relief.",
    start_url: "/",
    display: "standalone",
    background_color: "#0a111d",
    theme_color: "#0a111d",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
}

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ALL_LAYER_DEFINITIONS } from "@/lib/layers/registry";

// Licences live in docs/DATA_SOURCES.md; keep it in step with the code
const doc = readFileSync(join(__dirname, "../../../../docs/DATA_SOURCES.md"), "utf8");

/** The markdown table row that mentions `needle` */
const rowFor = (needle: string) =>
  doc.split("\n").find((line) => line.startsWith("|") && line.includes(needle));

describe("docs/DATA_SOURCES.md", () => {
  it("documents every overlay with a matching commercial-use marking", () => {
    for (const layer of ALL_LAYER_DEFINITIONS) {
      // e.g. "NASA GIBS — GOES-East ABI Band 13" -> row mentioning "GOES-East"
      const key = layer.source.name.split("—").pop()!.trim().split(" ").slice(0, 2).join(" ");
      const row = rowFor(key.includes("RainViewer") ? "RainViewer" : key);
      expect(row, `${layer.id}: no row for "${key}"`).toBeTruthy();
      expect(row!.includes(layer.source.commercialUse ? "✅" : "❌"), layer.id).toBe(true);
    }
  });

  it("documents both basemap providers", () => {
    expect(rowFor("OpenFreeMap")).toContain("✅");
    expect(rowFor("EOxCloudless")).toContain("❌");
    expect(rowFor("Blue Marble")).toContain("✅");
  });
});

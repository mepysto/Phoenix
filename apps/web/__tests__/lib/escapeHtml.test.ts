import { describe, expect, it } from "vitest";
import { escapeHtml } from "@/lib/escapeHtml";

describe("escapeHtml", () => {
  it("neutralises script/markup injection from feed text", () => {
    const payload = `<img src=x onerror="alert('x')">&`;
    expect(escapeHtml(payload)).toBe(
      "&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt;&amp;",
    );
  });

  it("leaves plain text unchanged", () => {
    expect(escapeHtml("M 6.2 Earthquake - Türkiye")).toBe("M 6.2 Earthquake - Türkiye");
  });
});

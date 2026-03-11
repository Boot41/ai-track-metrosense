import { describe, expect, it } from "vitest";
import { sanitizeArtifactHtml } from "@/lib/artifactSandbox";

describe("sanitizeArtifactHtml", () => {
  it("removes scripts, handlers, and external urls", () => {
    const html = sanitizeArtifactHtml(
      '<div onclick="alert(1)"><script>alert(1)</script><img src="https://example.com/a.png" /><a href="https://example.com">link</a><svg><rect width="10" height="10"/></svg></div>',
    );

    expect(html).not.toContain("script");
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("https://example.com");
    expect(html).toContain("svg");
  });
});

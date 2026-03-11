import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ArtifactRenderer from "@/components/chat/ArtifactRenderer";

describe("ArtifactRenderer", () => {
  it("renders a fallback when sanitized artifact content is empty", () => {
    render(
      <ArtifactRenderer
        artifact={{
          type: "html",
          title: "Unsafe chart",
          source: '<script>alert(1)</script>',
          description: "Unsafe chart description",
        }}
      />,
    );

    expect(screen.getByText("Chart could not be rendered")).toBeInTheDocument();
    expect(screen.getByText("Unsafe chart description")).toBeInTheDocument();
  });
});

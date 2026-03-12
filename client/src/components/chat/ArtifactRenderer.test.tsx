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

  it("renders table artifacts as a table", () => {
    render(
      <ArtifactRenderer
        artifact={{
          type: "table",
          title: "Bellandur Weather Comparison",
          columns: ["Metric", "September 2025", "October 2025"],
          rows: [["Avg Temp (C)", 23.3, 24.3]],
          description: "Monthly comparison",
        }}
      />,
    );

    expect(screen.getByRole("table", { name: "Bellandur Weather Comparison" })).toBeInTheDocument();
    expect(screen.getByText("September 2025")).toBeInTheDocument();
    expect(screen.getByText("24.3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open table" })).toBeInTheDocument();
  });
});

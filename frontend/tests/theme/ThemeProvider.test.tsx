import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ThemeProvider } from "../../src/theme/ThemeProvider";

describe("ThemeProvider", () => {
  it("always sets data-theme to dark — the product is intentionally single-theme", () => {
    document.documentElement.removeAttribute("data-theme");
    render(
      <ThemeProvider>
        <p>content</p>
      </ThemeProvider>,
    );
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});

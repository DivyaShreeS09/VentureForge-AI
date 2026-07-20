import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createStartup } from "../src/services/api";

describe("api client error handling", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws ApiError with the backend's detail message on a 422", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "description too short" }),
    });

    await expect(
      createStartup({ name: "", description: "x", funding_answers: {} }),
    ).rejects.toMatchObject({ status: 422, detail: "description too short" });
  });

  it("throws a network-error ApiError when fetch itself rejects", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new TypeError("network down"));

    await expect(
      createStartup({ name: "Nova", description: "A long enough description.", funding_answers: {} }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("throws a friendly timeout ApiError when the request is aborted", async () => {
    // Simulates the abort fetch would raise once the client's own request timeout fires —
    // asserting on that reaction directly rather than waiting out the real timeout duration.
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new DOMException("The operation was aborted.", "AbortError"));

    await expect(
      createStartup({ name: "Nova", description: "A long enough description.", funding_answers: {} }),
    ).rejects.toMatchObject({ detail: "The request took too long to respond. Please try again." });
  });
});

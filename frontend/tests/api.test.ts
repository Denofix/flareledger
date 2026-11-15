import { afterEach, describe, expect, it, vi } from "vitest";
import { request, ApiError } from "../src/lib/api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
describe("API failures remain distinguishable", () => {
  it("reports validation input errors without claiming an API outage", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              detail: [{ type: "string_too_long", loc: ["query", "q"] }],
            }),
            { status: 422 },
          ),
        ),
    );
    await expect(request("/search?q=" + "a".repeat(300))).rejects.toMatchObject(
      {
        status: 422,
        message:
          "The request contains invalid input. Check the supplied values and try again.",
      },
    );
  });
  it("preserves a JSON not-found response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: { code: "not_found" } }), {
          status: 404,
        }),
      ),
    );
    await expect(request("/records/missing")).rejects.toMatchObject({
      status: 404,
    });
  });
  it("rejects an HTML fallback instead of treating it as empty research data", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("<html>Wrong rewrite</html>", { status: 200 }),
        ),
    );
    await expect(request("/investigations")).rejects.toMatchObject({
      code: "invalid_response",
    });
  });
  it("can retain the structured Ask unavailable payload", async () => {
    const body = {
      error: { code: "llm_unavailable" },
      answer: null,
      retrieved_evidence: [],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify(body), { status: 503 })),
    );
    await expect(request("/ask", { method: "POST" }, [503])).resolves.toEqual(
      body,
    );
  });
  it("bounds requests that never return", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        }),
    );
    const result = request("/slow").catch((error) => error);
    await vi.advanceTimersByTimeAsync(18_000);
    const error = await result;
    expect(error).toBeInstanceOf(ApiError);
    if (!(error instanceof ApiError))
      throw new Error("Expected a structured timeout error");
    expect(error.code).toBe("timeout");
  });
});

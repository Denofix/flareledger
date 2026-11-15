export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public body?: unknown,
  ) {
    super(message);
  }
}

const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export async function request<T>(
  path: string,
  init: RequestInit = {},
  acceptStatuses: number[] = [],
  timeoutMs = 18_000,
): Promise<T> {
  const timeout = new AbortController();
  const signal = init.signal
    ? AbortSignal.any([init.signal, timeout.signal])
    : timeout.signal;
  const timer = window.setTimeout(() => timeout.abort(), timeoutMs);
  try {
    const response = await fetch(base + path, {
      ...init,
      signal,
      headers: { Accept: "application/json", ...init.headers },
      cache: "no-store",
    });
    const text = await response.text();
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      throw new ApiError(
        response.status,
        "invalid_response",
        "The API returned an unexpected response. Please try again.",
      );
    }
    if (!response.ok && !acceptStatuses.includes(response.status)) {
      const error = body as {
        error?: { code?: string; message?: string };
        detail?: { code?: string } | string;
      };
      const detail =
        typeof error.detail === "string" ? error.detail : undefined;
      throw new ApiError(
        response.status,
        error.error?.code || "request_failed",
        error.error?.message ||
          detail ||
          (response.status === 404
            ? "This research record was not found."
            : response.status === 422
              ? "The request contains invalid input. Check the supplied values and try again."
              : "The research API is temporarily unavailable."),
        body,
      );
    }
    return body as T;
  } catch (error) {
    if (init.signal?.aborted) throw error;
    if (timeout.signal.aborted)
      throw new ApiError(
        0,
        "timeout",
        "The request took too long. Please try again.",
      );
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      0,
      "network",
      "Unable to reach the research API. Check your connection and try again.",
    );
  } finally {
    window.clearTimeout(timer);
  }
}

export function query(
  values: Record<string, string | number | undefined>,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values))
    if (value !== undefined && value !== "") params.set(key, String(value));
  return params.size ? "?" + params.toString() : "";
}

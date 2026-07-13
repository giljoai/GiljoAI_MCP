/**
 * GiljoAI status page — health probe (Cloudflare Pages Function).
 *
 * Runs at /api/health on the status site itself, so the static page polls it
 * SAME-ORIGIN (no CORS). This function fetches app.giljo.ai/health server-side
 * (server-to-server — no CORS, and the app's strict no-wildcard CORS allowlist
 * is irrelevant here) and returns a small JSON verdict.
 *
 * Up/down classification accounts for the live giljo-app-fallback Worker, which
 * masks an origin outage as HTTP 200 + static fallback HTML:
 *   - 200 + application/json + {"status":"healthy"}  -> up
 *   - 200 + application/json + {"status":"degraded"}  -> degraded
 *   - 200 but NOT json (Worker serving the fallback page) -> down
 *   - any non-200, timeout, or network error              -> down
 *
 * Response: { state, httpStatus, latencyMs, detail, checkedAt }
 */

const TARGET = "https://app.giljo.ai/health";
const TIMEOUT_MS = 8000;

export async function onRequestGet() {
  const started = Date.now();
  let state = "down";
  let httpStatus = null;
  let detail = "";

  try {
    const resp = await fetch(TARGET, {
      method: "GET",
      headers: { accept: "application/json" },
      redirect: "manual",
      signal: AbortSignal.timeout(TIMEOUT_MS),
      cf: { cacheTtl: 0, cacheEverything: false },
    });

    httpStatus = resp.status;
    const contentType = resp.headers.get("content-type") || "";

    if (resp.status === 200 && contentType.includes("application/json")) {
      const body = await resp.json().catch(() => null);
      const status = body && typeof body.status === "string" ? body.status : "";
      if (status === "healthy") {
        state = "up";
        detail = "All systems operational.";
      } else if (status === "degraded") {
        state = "degraded";
        detail = "Some health checks are degraded.";
      } else {
        state = "degraded";
        detail = "Unexpected health payload.";
      }
    } else if (resp.status === 200) {
      // 200 but not JSON => the fallback Worker is serving its static page.
      state = "down";
      detail = "App is serving the fallback page.";
    } else {
      state = "down";
      detail = `Origin returned HTTP ${resp.status}.`;
    }
  } catch (err) {
    state = "down";
    detail = err && err.name === "TimeoutError"
      ? "Health check timed out."
      : "Origin unreachable.";
  }

  const payload = {
    state,
    httpStatus,
    latencyMs: Date.now() - started,
    detail,
    checkedAt: new Date().toISOString(),
  };

  return new Response(JSON.stringify(payload), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
    },
  });
}

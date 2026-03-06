import { SentinelAuth } from "@sentinel-auth/js";

const SENTINEL_URL =
  import.meta.env.VITE_SENTINEL_URL || "http://localhost:9003";

/** Shared SentinelAuth client instance used by both the React provider and apiFetch. */
export const sentinelClient = new SentinelAuth({
  sentinelUrl: SENTINEL_URL,
});

/**
 * Fetch wrapper for the demo backend API.
 * Uses SentinelAuth's fetchJson for automatic Bearer token injection, 401 retry, and JSON parsing.
 */
export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  return sentinelClient.fetchJson<T>(`/api${path}`, options);
}

import type { HomeData } from "@/lib/types";

// on the server the API is reached directly (in Docker: the api service); the browser's NEXT_PUBLIC_API_URL is
// empty in production (same origin behind Caddy) and so of no use here
const API = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** The homepage rows, fetched while the page renders on the server; null if the API does not answer in time
 *  (the browser then fetches them itself, as before). */
export async function loadHome(timeoutMs = 2500): Promise<HomeData | null> {
  try {
    const res = await fetch(`${API}/api/home`, { cache: "no-store", signal: AbortSignal.timeout(timeoutMs) });
    return res.ok ? ((await res.json()) as HomeData) : null;
  } catch {
    return null;
  }
}

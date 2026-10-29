import type { HomeData, MoodWorld, Movie, RankedMovie } from "@/lib/types";

export type ApiError = "network" | "not_found" | "server";
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  } catch {
    return { ok: false, error: "network" };
  }
  if (res.status === 404) return { ok: false, error: "not_found" };
  if (!res.ok) return { ok: false, error: "server" };
  return { ok: true, data: (await res.json()) as T };
}

export const getHome = () => apiGet<HomeData>("/api/home");
export const getWorlds = () => apiGet<MoodWorld[]>("/api/worlds");
export const getWorldMovies = (worldId: string, limit = 12) =>
  apiGet<RankedMovie[]>(`/api/worlds/${encodeURIComponent(worldId)}/movies?limit=${limit}`);
export const getMovie = (id: string) => apiGet<Movie>(`/api/movies/${encodeURIComponent(id)}`);
export const getRelated = (id: string, worldId?: string) =>
  apiGet<RankedMovie[]>(
    `/api/movies/${encodeURIComponent(id)}/related${worldId ? `?world_id=${encodeURIComponent(worldId)}` : ""}`,
  );

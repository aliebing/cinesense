import type { Criteria } from "@/lib/searchState";
import type { HomeData, MoodWorld, Movie, RankedMovie } from "@/lib/types";

export type ApiError = "network" | "not_found" | "server";
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    return { ok: false, error: "network" };
  }
  if (res.status === 404) return { ok: false, error: "not_found" };
  if (!res.ok) return { ok: false, error: "server" };
  try {
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return { ok: false, error: "server" };
  }
}

export function apiGet<T>(path: string): Promise<ApiResult<T>> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  return request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export type Tag = { idx: number; tag: string };
export type DiscoverResult = { items: RankedMovie[]; total: number; hidden_by_exclusion: number; extended_used: boolean };

export const getTags = () => apiGet<Tag[]>("/api/tags");
export const discover = (criteria: Criteria, offset = 0, limit = 20) =>
  apiPost<DiscoverResult>("/api/discover", { criteria, offset, limit });
export const search = (criteria: Criteria, offset = 0, limit = 20) =>
  apiPost<DiscoverResult>("/api/search", { criteria, offset, limit });

export const getHome = () => apiGet<HomeData>("/api/home");
export const getWorlds = () => apiGet<MoodWorld[]>("/api/worlds");
export const getWorldMovies = (worldId: string, limit = 12) =>
  apiGet<RankedMovie[]>(`/api/worlds/${encodeURIComponent(worldId)}/movies?limit=${limit}`);
export const getMovie = (id: string) => apiGet<Movie>(`/api/movies/${encodeURIComponent(id)}`);
export const getRelated = (id: string, worldId?: string) =>
  apiGet<RankedMovie[]>(
    `/api/movies/${encodeURIComponent(id)}/related${worldId ? `?world_id=${encodeURIComponent(worldId)}` : ""}`,
  );

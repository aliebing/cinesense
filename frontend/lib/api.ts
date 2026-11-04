import type { Criteria } from "@/lib/searchState";
import type { HomeData, MoodWorld, Movie, RankedMovie } from "@/lib/types";
import { USER_HEADER, userId } from "@/lib/user";

export type ApiError = "network" | "not_found" | "server" | "limited";
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError; message?: string };

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  let res: Response;
  try {
    const headers = { ...(init?.headers as Record<string, string> | undefined), [USER_HEADER]: userId() };
    res = await fetch(`${BASE_URL}${path}`, { cache: "no-store", ...init, headers });
  } catch {
    return { ok: false, error: "network" };
  }
  if (res.status === 404) return { ok: false, error: "not_found" };
  if (res.status === 429) {
    // the assistant's turn limits (backend/cinesense/web_api/limits.py): the server says what to show
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, error: "limited", message: body.detail };
  }
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
export type Relaxation = { id: string; label: string; count: number; criteria: Criteria };
export type DiscoverResult = {
  items: RankedMovie[];
  total: number;
  hidden_by_exclusion: number;
  extended_used: boolean;
  corrected_person?: string | null; // autocorrect: the person / title a misspelt search found
  corrected_title?: string | null;
  hidden_by?: Record<string, number>; // per exclusion ("genre:Horror", "tag:284"): films it hid in this search
  relaxations?: Relaxation[];
};

export const getTags = () => apiGet<Tag[]>("/api/tags");
export type Suggestion = { value: string; label: string };
/** Typing suggestions for the advanced search (catalogue titles or people, typo-tolerant). */
export const suggest = (field: "title" | "person", q: string, role: string = "any") =>
  apiGet<Suggestion[]>(`/api/suggest?${new URLSearchParams({ field, q, role })}`);
/** `fillImages: false` skips the Streaming API image lookups (homepage background rows spend no budget). */
export const discover = (criteria: Criteria, offset = 0, limit = 20, fillImages = true) =>
  apiPost<DiscoverResult>("/api/discover", fillImages ? { criteria, offset, limit } : { criteria, offset, limit, fill_images: false });
export const search = (criteria: Criteria, offset = 0, limit = 20, relaxedFrom?: Criteria) =>
  apiPost<DiscoverResult>("/api/search", { criteria, offset, limit, ...(relaxedFrom ? { relaxed_from: relaxedFrom } : {}) });

export const getHome = () => apiGet<HomeData>("/api/home");
export const getWorlds = () => apiGet<MoodWorld[]>("/api/worlds");
export const getWorldMovies = (worldId: string, limit = 12) =>
  apiGet<RankedMovie[]>(`/api/worlds/${encodeURIComponent(worldId)}/movies?limit=${limit}`);
export const getMovie = (id: string) => apiGet<Movie>(`/api/movies/${encodeURIComponent(id)}`);
export const getRelated = (id: string, worldId?: string) =>
  apiGet<RankedMovie[]>(
    `/api/movies/${encodeURIComponent(id)}/related${worldId ? `?world_id=${encodeURIComponent(worldId)}` : ""}`,
  );

export type FilmRef = { id: string; title: string; year: number | null };
export type ProfileSummary = { liked: FilmRef[]; disliked: FilmRef[]; taste: string[] };
export const sendFeedback = (filmId: string, value: -1 | 0 | 1) =>
  apiPost<ProfileSummary>("/api/feedback", { film_id: filmId, value });
export const getProfile = () => apiGet<ProfileSummary>("/api/profile");
export const resetProfile = () => request<ProfileSummary>("/api/profile", { method: "DELETE" });
/** The embedded player could not play this trailer; the backend stops offering it. */
export const reportTrailer = (videoId: string) => apiPost<null>("/api/trailers/report", { video_id: videoId });

/** One agent turn with everything behind it, for the technical review page (/tech). */
export type InspectFilm = {
  id: string;
  imdb_id?: string | null;
  title: string;
  year: number | null;
  match_percent: number | null;
  score: number | null;
  reasons: string[];
  genres: string[];
  worlds: string[];
  directors: string[];
  cast: string[];
  runtime_min: number | null;
  ml_rating: number | null;
  ml_rating_count: number | null;
  overview: string | null;
};
export type InspectResult = {
  reply: string;
  picks: number;
  results: InspectFilm[];
  criteria: Criteria;
  criteria_summary: string;
  tags: { tag: string; weight: number; mode: string }[];
  proposals: { idx: number; tag: string; mode: string }[];
  tools: { name: string; args: Record<string, unknown>; result: string | null }[];
  prompts: { agent?: string; explain?: string; explain_input?: string };
  model: string;
  usage: { input_tokens?: number; output_tokens?: number };
  cost_usd: number;
  latency_s: number;
  rounds: number;
  grounding_fallback: boolean;
  grounding_reason: string[];
};
export const inspectTurn = (threadId: string, message: string, criteria: Criteria) =>
  apiPost<InspectResult>("/api/inspect", { thread_id: threadId, message, criteria });

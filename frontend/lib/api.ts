import type { Criteria } from "@/lib/searchState";
import type { HomeData, MoodWorld, Movie, RankedMovie } from "@/lib/types";
import { ensureUserId, userHeaders } from "@/lib/user";

export type ApiError = "network" | "not_found" | "server" | "limited";
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError; message?: string };

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  let res: Response;
  try {
    const headers = { ...(init?.headers as Record<string, string> | undefined), ...userHeaders() };
    // credentials: the admin session cookie also reaches the API on another port in local development
    res = await fetch(`${BASE_URL}${path}`, { cache: "no-store", credentials: "include", ...init, headers });
  } catch {
    return { ok: false, error: "network" };
  }
  if (res.status === 404) return { ok: false, error: "not_found" };
  if (res.status === 429) {
    // the assistant's turn limits (backend/cinesense/web_api/limits.py): the server says what to show
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, error: "limited", message: body.detail };
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
    return { ok: false, error: "server", message: typeof body.detail === "string" ? body.detail : undefined };
  }
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
  total_capped?: boolean; // the mood search kept only its best films: total is a lower bound ("500+")
  hidden_by?: Record<string, number>; // per exclusion ("genre:Horror", "tag:284"): films it hid in this search
  match_counts?: Record<string, number>; // floor % ("50" … "90") -> films from it, over the whole search
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
/** `fillImages: false` for further pages of the results grid: no Streaming API image lookups, no YouTube searches. */
export const search = (criteria: Criteria, offset = 0, limit = 20, relaxedFrom?: Criteria, fillImages = true) =>
  apiPost<DiscoverResult>("/api/search", {
    criteria,
    offset,
    limit,
    ...(relaxedFrom ? { relaxed_from: relaxedFrom } : {}),
    ...(fillImages ? {} : { fill_images: false }),
  });

export const getHome = () => apiGet<HomeData>("/api/home");
export const getWorlds = () => apiGet<MoodWorld[]>("/api/worlds");
export const getWorldMovies = (worldId: string, limit = 12) =>
  apiGet<RankedMovie[]>(`/api/worlds/${encodeURIComponent(worldId)}/movies?limit=${limit}`);
/** how one film carries each wished mood (percent null: no mood data for it) */
export type MoodFit = { tag: string; mode: "prefer" | "must" | "not"; percent: number | null };
export const fitMovie = (id: string, criteria: Criteria) => apiPost<MoodFit[]>(`/api/movies/${encodeURIComponent(id)}/fit`, criteria);
export const getMovie = (id: string) => apiGet<Movie>(`/api/movies/${encodeURIComponent(id)}`);
/** films like this one, within a world (by the film's own mood tags) */
export const getRelated = (id: string, worldId?: string, limit?: number) => {
  const q = new URLSearchParams();
  if (worldId) q.set("world_id", worldId);
  if (limit) q.set("limit", String(limit));
  const qs = q.toString();
  return apiGet<RankedMovie[]>(`/api/movies/${encodeURIComponent(id)}/related${qs ? `?${qs}` : ""}`);
};

export type FilmRef = { id: string; title: string; year: number | null };
export type ProfileSummary = { liked: FilmRef[]; disliked: FilmRef[]; taste: string[] };
/** 👍/👎: the first rating creates the browser's anonymous id (lib/user.ts). */
export const sendFeedback = (filmId: string, value: -1 | 0 | 1) => {
  ensureUserId();
  return apiPost<ProfileSummary>("/api/feedback", { film_id: filmId, value });
};
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

/** One saved evaluation run in the history (backend/cinesense/web_api/eval_view.py). */
export type EvalRunOverview = {
  run: string; // "2026-11-05_1554"
  scenarios: number;
  scenarios_total: number; // all scenarios at the time: a run of a selection has fewer
  passed: number;
  model: string | null;
  cost_usd: number; // agent and judge
  stopped: boolean;
  source: "local" | "server";
  grounding_raw: number | null;
  agent_judge: number | null; // mean LLM-judge score (1-5) of the agent's top 5
  ranker_judge: Record<string, number | null>; // per ranker in the comparison
};
export type EvalCheck = { ok: boolean; why: string[]; applies: boolean };
export type EvalScenario = {
  id: string;
  category: string;
  failure: string | null;
  turns: string[];
  tools_called: string[];
  tools_per_turn?: string[][]; // runs before 2026-11-05 only have the flat list
  reply: string;
  results: string[];
  passed: boolean;
  error: string | null;
  checks: Record<string, EvalCheck>;
  judge?: { score: number | null; reason: string };
  latency_s: number;
  cost_usd?: number;
  grounding_fallback?: boolean;
  grounding_reason?: string[];
  relaxed?: string[];
};
export type EvalComparisonRow = {
  id: string;
  metrics: Record<string, Record<string, number | null>>;
  top: Record<string, string[]>;
  judge: Record<string, number | null>;
};
export type EvalRun = EvalRunOverview & {
  summary: Record<string, unknown> & { counts?: Record<string, [number, number]> };
  results: EvalScenario[];
  comparison: { rows?: EvalComparisonRow[]; judge_cost_usd?: number };
  rankers: Record<string, Record<string, number | null>>;
};

export const getEvalRuns = () => apiGet<EvalRunOverview[]>("/api/eval/runs");
export const getEvalRun = (run: string) => apiGet<EvalRun>(`/api/eval/runs/${encodeURIComponent(run)}`);

/** Starting a run on /admin/evaluation. Prices are USD per million tokens. */
export type EvalModel = {
  id: string;
  label: string;
  input_per_million: number;
  output_per_million: number;
  price_source: "openrouter" | "table";
  agent_per_scenario_usd: number | null;
};
export type EvalOptions = {
  models: EvalModel[];
  default_model: string;
  judge: Omit<EvalModel, "agent_per_scenario_usd"> & { per_call_usd: number | null };
  estimate_basis: string | null;
  scenarios: { id: string; category: string; turns: string[]; compared: boolean }[];
  presets: Record<string, string[]>;
};
export type EvalLiveResult = {
  id: string;
  category: string;
  turns: string[];
  passed: boolean;
  reply: string;
  results: string[];
  judge?: { score: number | null; reason: string } | null;
  latency_s: number | null;
  cost_usd: number | null;
  error: string | null;
  failed_checks: string[];
  grounding_fallback: boolean;
};
export type EvalLive = {
  status: "idle" | "running" | "stopping" | "done" | "stopped" | "failed";
  model?: string;
  selection?: string[];
  total?: number;
  done?: number;
  passed?: number;
  cost_usd?: number;
  current?: { id: string; turns: string[] } | null;
  phase?: "scenarios" | "comparing" | "saved";
  results?: EvalLiveResult[];
  started?: number;
  run?: string | null;
  error?: string | null;
};
export const getEvalOptions = () => apiGet<EvalOptions>("/api/eval/options");
export const startEval = (model: string, scenarioIds: string[]) =>
  apiPost<EvalLive>("/api/eval/start", { model, scenario_ids: scenarioIds });
export const getEvalLive = () => apiGet<EvalLive>("/api/eval/live");
export const stopEval = () => apiPost<EvalLive>("/api/eval/stop", {});

/** The visitor log on /admin/visitors (backend/cinesense/web_api/chat_log.py). */
export type VisitorTurn = {
  id: number;
  ts: string;
  scope: "chat" | "tech";
  visitor: string | null;
  thread: string | null;
  message: string | null;
  films: number;
  tools: string[];
  grounding_fallback: boolean;
  guarded: boolean;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  duration_ms: number | null;
  error: string | null;
};
export type VisitorPage = {
  items: VisitorTurn[];
  total: number;
  sums: { count: number; cost_usd: number; avg_duration_ms: number | null; visitors: number };
};
export type VisitorTurnDetail = Omit<VisitorTurn, "films" | "tools"> & {
  reply: string | null;
  criteria: Record<string, unknown> | null;
  criteria_summary: string | null;
  films: { title: string; year: number | null; match: number | null }[];
  tools: { name: string; args: Record<string, unknown> }[];
  relaxed: string[];
  grounding_reason: string[];
  model: string | null;
  conversation: { id: number; ts: string; message: string | null }[];
};
export const getVisitors = (scope: "chat" | "tech" | null, offset = 0, limit = 50) =>
  apiGet<VisitorPage>(`/api/admin/visitors?${scope ? `scope=${scope}&` : ""}offset=${offset}&limit=${limit}`);
export const getVisitorTurn = (id: number) => apiGet<VisitorTurnDetail>(`/api/admin/visitors/${id}`);

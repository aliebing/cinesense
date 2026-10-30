import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { emptyCriteria } from "@/lib/searchState";
import type { RankedMovie } from "@/lib/types";
import { sampleRanked, sampleWorlds } from "./fixtures";

const discover = vi.fn();
vi.mock("@/lib/api", () => ({ discover: (...a: unknown[]) => discover(...a) }));

import { HITS_ROW_ID, preferPictured, topWorlds, useSearchRows } from "@/lib/searchRows";

const ranked = (ids: string[], world: string): RankedMovie[] =>
  sampleRanked(ids.length).map((r, i) => ({ ...r, movie: { ...r.movie, id: ids[i], world_ids: [world] } }));

beforeEach(() => discover.mockReset());

it("topWorlds: the worlds the hits fall into most often, ties in catalogue order", () => {
  const hits = [...ranked(["a", "b"], "action"), ...ranked(["c"], "suspense")];
  expect(topWorlds(hits, ["suspense", "action", "comedy"], 3)).toEqual(["action", "suspense"]);
  expect(topWorlds(ranked(["a"], "x").concat(ranked(["b"], "y")), ["y", "x"], 1)).toEqual(["y"]);
});

it("preferPictured: title-only tiles only when there are too few pictures", async () => {
  const { sampleMovies } = await import("./fixtures");
  const bare = (m: ReturnType<typeof sampleMovies>[number]) => ({ ...m, horizontal_poster_url: null, backdrop_url: null });
  const movies = sampleMovies(6).map((m, i) => (i % 2 ? bare(m) : m));
  expect(preferPictured(movies)).toHaveLength(6); // only 3 pictured: keep all
  const more = sampleMovies(8).map((m, i) => (i === 0 ? bare(m) : m));
  expect(preferPictured(more).map((m) => m.id)).not.toContain("demo-01");
});

it("without criteria there are no search rows (the homepage keeps its world rows)", () => {
  const { result } = renderHook(() => useSearchRows(emptyCriteria(), sampleWorlds, 4));
  expect(result.current).toBeNull();
  expect(discover).not.toHaveBeenCalled();
});

it("first row: the hits; then one row per matching world with the same criteria, no film twice", async () => {
  const criteria = { ...emptyCriteria(), tags: [{ idx: 7, weight: 8, mode: "prefer" as const }] };
  discover.mockImplementation(async (c?: { world_id: string | null }) => ({
    ok: true,
    data: {
      items: c?.world_id ? ranked(["h1", "w1", "w2", "w3", "w4"], c.world_id) : ranked(["h1", "h2", "h3", "h4", "h5"], "action"),
      total: 5,
      hidden_by_exclusion: 0,
      extended_used: false,
    },
  }));
  const { result } = renderHook(() => useSearchRows(criteria, sampleWorlds, 4));
  await waitFor(() => expect(result.current).not.toBeNull());
  const rows = result.current!;
  expect(rows[0].world.id).toBe(HITS_ROW_ID);
  expect(rows[0].movies.map((m) => m.id)).toEqual(["h1", "h2", "h3", "h4", "h5"]);
  expect(rows[1].world.id).toBe("action");
  expect(rows[1].movies.map((m) => m.id)).toEqual(["w1", "w2", "w3", "w4"]);
  expect(discover).toHaveBeenCalledWith({ ...criteria, world_id: "action" }, 0, expect.any(Number), false);
});

it("no hits: no search rows", async () => {
  const criteria = { ...emptyCriteria(), max_runtime_min: 10 };
  discover.mockResolvedValue({ ok: true, data: { items: [], total: 0, hidden_by_exclusion: 0, extended_used: false } });
  const { result } = renderHook(() => useSearchRows(criteria, sampleWorlds, 4));
  await waitFor(() => expect(discover).toHaveBeenCalled());
  expect(result.current).toBeNull();
});

it("a world whose films lack pictures waits behind worlds with pictures", async () => {
  const criteria = { ...emptyCriteria(), tags: [{ idx: 7, weight: 8, mode: "prefer" as const }] };
  const bare = (rs: RankedMovie[]) => rs.map((r) => ({ ...r, movie: { ...r.movie, horizontal_poster_url: null, backdrop_url: null } }));
  const hits = [...ranked(["h1", "h2", "h3"], "suspense"), ...ranked(["h4"], "action")];
  discover.mockImplementation(async (c?: { world_id: string | null }) => ({
    ok: true,
    data: {
      items:
        c?.world_id === "suspense"
          ? bare(ranked(["s1", "s2", "s3", "s4"], "suspense"))
          : c?.world_id === "action"
            ? ranked(["a1", "a2", "a3", "a4"], "action")
            : hits,
      total: 4,
      hidden_by_exclusion: 0,
      extended_used: false,
    },
  }));
  const { result } = renderHook(() => useSearchRows(criteria, sampleWorlds, 3));
  await waitFor(() => expect(result.current).not.toBeNull());
  expect(result.current!.map((r) => r.world.id)).toEqual([HITS_ROW_ID, "action", "suspense"]);
});

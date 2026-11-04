"use client";

import { useEffect, useState } from "react";
import { discover } from "@/lib/api";
import { type Criteria, hasAnyCriteria } from "@/lib/searchState";
import type { MoodWorld, Movie, RankedMovie, TileRow } from "@/lib/types";

export const HITS_ROW_ID = "search-hits";
const HITS = 24;
const MIDDLE_MAX = 12; // the middle row runs large tiles: the closest matches only, so a loop stays short
const PER_WORLD = 24;
const MIN_ROW = 4; // fewer films than this would loop visibly
const DEBOUNCE_MS = 400; // chips can change in quick succession

const hasPicture = (m: Movie) => Boolean(m.horizontal_poster_url || m.backdrop_url);

/** Films with a picture first-class: title-only tiles only when a row would otherwise be too short. */
export function preferPictured(movies: Movie[]): Movie[] {
  const pictured = movies.filter(hasPicture);
  return pictured.length >= MIN_ROW ? pictured : movies;
}

/** The worlds the hits fall into most often; ties keep the catalogue order. */
export function topWorlds(hits: RankedMovie[], order: string[], n: number): string[] {
  const count = new Map<string, number>();
  for (const r of hits) for (const w of r.movie.world_ids) count.set(w, (count.get(w) ?? 0) + 1);
  const rank = (w: string) => (order.indexOf(w) < 0 ? order.length : order.indexOf(w));
  return [...count.keys()].sort((a, b) => count.get(b)! - count.get(a)! || rank(a) - rank(b)).slice(0, n);
}

/** The hits (the short list) go in the middle, the other candidates above and below. */
export function aroundTheShortList(short: TileRow, others: TileRow[]): TileRow[] {
  const mid = Math.floor(others.length / 2);
  return [...others.slice(0, mid), short, ...others.slice(mid)];
}

/** A search with few hits finds too few worlds for `count` rows: fill up with the homepage's world rows (worlds
 *  not shown yet, films not shown yet), so the homepage always shows its full set of rows; the hits stay in the middle. */
export function padRows(rows: TileRow[], worldRows: TileRow[], count: number): TileRow[] {
  if (rows.length >= count) return rows;
  const short = rows.find((r) => r.world.id === HITS_ROW_ID);
  const others = rows.filter((r) => r !== short);
  const seen = new Set(rows.flatMap((r) => r.movies.map((m) => m.id)));
  const worlds = new Set(rows.map((r) => r.world.id));
  for (const row of worldRows) {
    if (others.length + (short ? 1 : 0) >= count) break;
    if (worlds.has(row.world.id)) continue;
    const movies = row.movies.filter((m) => !seen.has(m.id));
    if (movies.length < MIN_ROW) continue;
    movies.forEach((m) => seen.add(m.id));
    others.push({ world: row.world, movies });
  }
  return short ? aroundTheShortList(short, others) : others;
}

/** Homepage tile rows for the current search (set in the chat or with the chips): the hits in the middle, led by the
 *  chat's picks (`picks`, shown larger), around them one row per world the hits belong to, with the same criteria and no film twice. `null` while there is no search (or no hit),
 *  so the homepage shows its world rows. Uses /api/discover: same ranking, never the paid live search; only the hits
 *  row may look up missing images (like the result page), the world rows use the pictures already known. */
export function useSearchRows(criteria: Criteria, worlds: MoodWorld[], rowCount: number, picks: Movie[] = []): TileRow[] | null {
  return useSearchRowsWithStatus(criteria, worlds, rowCount, picks).rows;
}

/** `useSearchRows` plus `loading`: true from a change of the search until its rows are there (the homepage's loading
 *  bar). The rows of the previous search stay meanwhile. */
export function useSearchRowsWithStatus(
  criteria: Criteria,
  worlds: MoodWorld[],
  rowCount: number,
  picks: Movie[] = [],
): { rows: TileRow[] | null; loading: boolean } {
  const [rows, setRows] = useState<TileRow[] | null>(null);
  const [doneKey, setDoneKey] = useState<string | null>(null);
  const active = hasAnyCriteria(criteria);
  const key = active ? JSON.stringify({ ...criteria, world_id: null }) : null;
  const order = worlds.map((w) => w.id).join(",");
  const pickKey = JSON.stringify(picks.slice(0, 5));
  const runKey = `${key}|${order}|${rowCount}|${pickKey}`;

  useEffect(() => {
    let live = true;
    if (key === null) {
      void Promise.resolve().then(() => live && setRows(null));
      return () => {
        live = false;
      };
    }
    const c = JSON.parse(key) as Criteria;
    const timer = setTimeout(async () => {
      const first = await discover(c, 0, HITS);
      if (!live) return;
      const hits = first.ok ? first.data.items : [];
      const found = new Map(hits.map((r) => [r.movie.id, r.movie]));
      // the hits carry looked-up pictures, the chat's copies may not
      const chosen = (JSON.parse(pickKey) as Movie[]).map((m) => found.get(m.id) ?? m);
      if (hits.length === 0 && chosen.length === 0) {
        setDoneKey(runKey);
        return setRows(null);
      }
      const featured = chosen.map((m) => m.id);
      const rest = preferPictured(hits.map((r) => r.movie)).filter((m) => !featured.includes(m.id));
      const middle = [...chosen, ...rest].slice(0, Math.max(MIDDLE_MAX, chosen.length));
      const short: TileRow = { world: hitsWorld(), movies: middle, picked: true, featured };
      const seen = new Set(middle.map((m) => m.id)); // hits past the middle row may still run in the rows around it
      const out: TileRow[] = [];
      // worlds by how many hits they hold; a world whose films have too few pictures waits behind the others
      const fallback: TileRow[] = [];
      for (const id of topWorlds(hits, order.split(","), worlds.length)) {
        if (out.length >= rowCount - 1) break;
        const world = worlds.find((w) => w.id === id);
        if (!world) continue;
        const r = await discover({ ...c, world_id: id }, 0, PER_WORLD + HITS, false); // no image lookups: no budget
        if (!live) return;
        const fresh = (r.ok ? r.data.items : []).map((x) => x.movie).filter((m) => !seen.has(m.id));
        const pictured = fresh.filter(hasPicture);
        if (pictured.length >= MIN_ROW) {
          const movies = pictured.slice(0, PER_WORLD);
          movies.forEach((m) => seen.add(m.id));
          out.push({ world, movies });
        } else if (fresh.length >= MIN_ROW) fallback.push({ world, movies: fresh.slice(0, PER_WORLD) });
      }
      for (const row of fallback) {
        if (out.length >= rowCount - 1) break;
        const movies = row.movies.filter((m) => !seen.has(m.id));
        movies.forEach((m) => seen.add(m.id));
        if (movies.length >= MIN_ROW) out.push({ ...row, movies });
      }
      setRows(aroundTheShortList(short, out));
      setDoneKey(runKey);
    }, DEBOUNCE_MS);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [key, order, rowCount, pickKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return { rows, loading: key !== null && doneKey !== runKey };
}

function hitsWorld(): MoodWorld {
  return { id: HITS_ROW_ID, title: "Your search", kicker: "", subtitle: "", tint: "#f3c76b", genres: [] };
}

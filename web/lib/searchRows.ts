"use client";

import { useEffect, useState } from "react";
import { discover } from "@/lib/api";
import { type Criteria, hasAnyCriteria } from "@/lib/searchState";
import type { MoodWorld, Movie, RankedMovie, TileRow } from "@/lib/types";

export const HITS_ROW_ID = "search-hits";
const HITS = 24;
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

/** Homepage tile rows for the current search (set in the chat or with the chips): first the hits, then one row per
 *  world the hits belong to, with the same criteria and no film twice. `null` while there is no search (or no hit),
 *  so the homepage shows its world rows. Uses /api/discover: same ranking, never the paid live search; only the hits
 *  row may look up missing images (like the result page), the world rows use the pictures already known. */
export function useSearchRows(criteria: Criteria, worlds: MoodWorld[], rowCount: number): TileRow[] | null {
  const [rows, setRows] = useState<TileRow[] | null>(null);
  const active = hasAnyCriteria(criteria);
  const key = active ? JSON.stringify({ ...criteria, world_id: null }) : null;
  const order = worlds.map((w) => w.id).join(",");

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
      if (hits.length === 0) return setRows(null);
      const seen = new Set(hits.map((r) => r.movie.id));
      const out: TileRow[] = [{ world: hitsWorld(), movies: preferPictured(hits.map((r) => r.movie)) }];
      // worlds by how many hits they hold; a world whose films have too few pictures waits behind the others
      const fallback: TileRow[] = [];
      for (const id of topWorlds(hits, order.split(","), worlds.length)) {
        if (out.length >= rowCount) break;
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
        if (out.length >= rowCount) break;
        const movies = row.movies.filter((m) => !seen.has(m.id));
        movies.forEach((m) => seen.add(m.id));
        if (movies.length >= MIN_ROW) out.push({ ...row, movies });
      }
      setRows(out);
    }, DEBOUNCE_MS);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [key, order, rowCount]); // eslint-disable-line react-hooks/exhaustive-deps

  return rows;
}

function hitsWorld(): MoodWorld {
  return { id: HITS_ROW_ID, title: "Your search", kicker: "", subtitle: "", tint: "#f3c76b", genres: [] };
}

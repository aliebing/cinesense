"use client";

import { useSyncExternalStore } from "react";

export type TagMode = "prefer" | "must" | "not";
export type TagCriterion = { idx: number; weight: number; mode: TagMode };

/** Mirrors the backend SearchCriteria (backend/cinesense/core/criteria.py). */
export type Criteria = {
  tags: TagCriterion[];
  plot_query: string | null;
  title: string | null;
  person: string | null;
  person_role: "cast" | "director" | "any";
  exclude_genres: string[];
  exclude_people: string[]; // "without Stallone": their films drop out (at most 5)
  world_id: string | null;
  availability: "cinema" | "stream" | "any";
  kind: "film" | "documentary" | "any";
  max_runtime_min: number | null;
  year_from: number | null;
  year_to: number | null;
  original_language: string | null;
  min_rating_count: number;
  extended: boolean;
};

export function emptyCriteria(): Criteria {
  return {
    tags: [],
    plot_query: null,
    title: null,
    person: null,
    person_role: "any",
    exclude_genres: [],
    exclude_people: [],
    world_id: null,
    availability: "any",
    kind: "any",
    max_runtime_min: null,
    year_from: null,
    year_to: null,
    original_language: null,
    min_rating_count: 0,
    extended: false,
  };
}

const KEY = "cinesense.search";
let state: Criteria | null = null;
const listeners = new Set<() => void>();

function load(): Criteria {
  if (state) return state;
  try {
    const raw = typeof window !== "undefined" ? window.sessionStorage.getItem(KEY) : null;
    state = raw ? { ...emptyCriteria(), ...JSON.parse(raw) } : emptyCriteria();
  } catch {
    state = emptyCriteria();
  }
  return state!;
}

/** Change some fields of the current search (e.g. the autocorrected person), keeping the rest. */
export function patchSearchState(patch: Partial<Criteria>) {
  setSearchState({ ...load(), ...patch });
}

export function setSearchState(next: Criteria) {
  state = next;
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage may be unavailable; state still lives in memory */
  }
  listeners.forEach((l) => l());
}

const serverSnapshot = emptyCriteria();

/** Shared search state: chip bar, advanced search and (Plan 3) the chat agent read and write it. */
export function useSearchState(): [Criteria, (c: Criteria) => void] {
  const value = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    load,
    () => serverSnapshot,
  );
  return [value, setSearchState];
}

/** "🚫 No horror": exclude the genre and add a not-tag for horror. */
export function withNoHorror(c: Criteria, horrorIdx: number | null): Criteria {
  const genres = c.exclude_genres.includes("Horror") ? c.exclude_genres : [...c.exclude_genres, "Horror"];
  const tags =
    horrorIdx === null
      ? c.tags
      : [...c.tags.filter((t) => t.idx !== horrorIdx), { idx: horrorIdx, weight: 5, mode: "not" as const }];
  return { ...c, exclude_genres: genres, tags };
}

export function hasAnyCriteria(c: Criteria): boolean {
  const e = emptyCriteria();
  return JSON.stringify({ ...c, world_id: null }) !== JSON.stringify({ ...e, world_id: null });
}

/** Session steering (⚡ More action, 😂 Funnier): add the tag as prefer, or strengthen it by 2 (max 10). */
export function steer(c: Criteria, idx: number): Criteria {
  const current = c.tags.find((t) => t.idx === idx && t.mode !== "not");
  const weight = current ? Math.min(10, current.weight + 2) : 6;
  return { ...c, tags: [...c.tags.filter((t) => t.idx !== idx), { idx, weight, mode: "prefer" }] };
}

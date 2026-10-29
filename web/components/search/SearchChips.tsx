"use client";

import { useMemo, useState } from "react";
import type { Criteria, TagCriterion, TagMode } from "@/lib/searchState";

export type Tag = { idx: number; tag: string };
type Props = { tags: Tag[]; criteria: Criteria; onChange: (c: Criteria) => void; hiddenCount?: number };

const NEXT_MODE: Record<TagMode, TagMode> = { prefer: "must", must: "not", not: "prefer" };
const DOTS = [1, 2, 3, 4, 5];

/** The visible search state: mood tags (weight / must / not), exclusions, people and filters. */
export default function SearchChips({ tags, criteria, onChange, hiddenCount = 0 }: Props) {
  const [picking, setPicking] = useState(false);
  const [query, setQuery] = useState("");
  const name = useMemo(() => new Map(tags.map((t) => [t.idx, t.tag])), [tags]);
  const used = new Set(criteria.tags.map((t) => t.idx));
  const matches = query.trim()
    ? tags.filter((t) => !used.has(t.idx) && t.tag.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 8)
    : [];

  const setTag = (idx: number, patch: Partial<TagCriterion>) =>
    onChange({ ...criteria, tags: criteria.tags.map((t) => (t.idx === idx ? { ...t, ...patch } : t)) });
  const removeTag = (idx: number) => onChange({ ...criteria, tags: criteria.tags.filter((t) => t.idx !== idx) });
  const addTag = (idx: number) => {
    onChange({ ...criteria, tags: [...criteria.tags, { idx, weight: 6, mode: "prefer" }] });
    setQuery("");
    setPicking(false);
  };

  const mood = criteria.tags.filter((t) => t.mode !== "not");
  const excluded = criteria.tags.filter((t) => t.mode === "not");
  const others: { key: string; label: string; clear: Partial<Criteria>; aria: string }[] = [];
  if (criteria.person) others.push({ key: "person", label: `👤 ${criteria.person}`, clear: { person: null }, aria: `Remove person ${criteria.person}` });
  if (criteria.title) others.push({ key: "title", label: `🔤 “${criteria.title}”`, clear: { title: null }, aria: `Remove title ${criteria.title}` });
  if (criteria.plot_query) others.push({ key: "plot", label: `📖 “${criteria.plot_query}”`, clear: { plot_query: null }, aria: "Remove plot search" });
  if (criteria.availability === "stream") others.push({ key: "stream", label: "📺 Streaming (DE)", clear: { availability: "any" }, aria: "Remove streaming filter" });
  if (criteria.availability === "cinema") others.push({ key: "cinema", label: "🎬 In cinemas", clear: { availability: "any" }, aria: "Remove cinema filter" });
  if (criteria.max_runtime_min) others.push({ key: "runtime", label: `< ${criteria.max_runtime_min} min`, clear: { max_runtime_min: null }, aria: "Remove runtime limit" });
  if (criteria.kind !== "any") others.push({ key: "kind", label: criteria.kind === "documentary" ? "Documentaries" : "Feature films", clear: { kind: "any" }, aria: "Remove kind filter" });
  if (criteria.year_from || criteria.year_to) others.push({ key: "year", label: `${criteria.year_from ?? "…"}–${criteria.year_to ?? "…"}`, clear: { year_from: null, year_to: null }, aria: "Remove year range" });
  if (criteria.original_language) others.push({ key: "lang", label: `Language: ${criteria.original_language}`, clear: { original_language: null }, aria: "Remove language filter" });

  return (
    <div className="search-chips" aria-label="Search criteria">
      <div className="chips-line">
        {mood.map((t) => {
          const label = name.get(t.idx) ?? `tag ${t.idx}`;
          const dots = Math.round(t.weight / 2);
          return (
            <span key={t.idx} className={`chip chip--mood ${t.mode === "must" ? "chip--must" : ""}`}>
              <span className="chip__name">{label}</span>
              <span className="chip__dots">
                {DOTS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={d <= dots ? "on" : ""}
                    aria-label={`Weight ${d} of 5 for ${label}`}
                    onClick={() => setTag(t.idx, { weight: d * 2 })}
                  />
                ))}
              </span>
              <button
                type="button"
                className="chip__mode"
                aria-label={`Mode for ${label}: ${t.mode}`}
                onClick={() => setTag(t.idx, { mode: NEXT_MODE[t.mode] })}
              >
                {t.mode === "must" ? "MUST" : "prefer"}
              </button>
              <button type="button" className="chip__x" aria-label={`Remove ${label}`} onClick={() => removeTag(t.idx)}>
                ×
              </button>
            </span>
          );
        })}
        <span className="chip-add">
          <button type="button" className="chip chip--add" onClick={() => setPicking((p) => !p)}>
            + Tag
          </button>
          {picking && (
            <span className="tag-picker">
              <input
                type="search"
                aria-label="Find a mood tag"
                placeholder="e.g. medieval, dark, space travel"
                value={query}
                autoFocus
                onChange={(e) => setQuery(e.target.value)}
              />
              {matches.map((t) => (
                <button key={t.idx} type="button" onClick={() => addTag(t.idx)}>
                  {t.tag}
                </button>
              ))}
            </span>
          )}
        </span>
      </div>
      {(excluded.length > 0 || criteria.exclude_genres.length > 0) && (
        <div className="chips-line">
          <span className="chips-heading">Excluded</span>
          {excluded.map((t) => {
            const label = name.get(t.idx) ?? `tag ${t.idx}`;
            return (
              <span key={t.idx} className="chip chip--excluded">
                <span aria-hidden="true">🚫</span> <s>{label}</s>
                <button type="button" className="chip__mode" aria-label={`Mode for ${label}: not`} onClick={() => setTag(t.idx, { mode: "prefer" })}>
                  NOT
                </button>
                <button type="button" className="chip__x" aria-label={`Remove ${label}`} onClick={() => removeTag(t.idx)}>
                  ×
                </button>
              </span>
            );
          })}
          {criteria.exclude_genres.map((g) => (
            <span key={g} className="chip chip--excluded">
              <span>🚫 {g} (genre)</span>
              <button
                type="button"
                className="chip__x"
                aria-label={`Remove excluded genre ${g}`}
                onClick={() => onChange({ ...criteria, exclude_genres: criteria.exclude_genres.filter((x) => x !== g) })}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      {hiddenCount > 0 && <p className="chips-hidden">→ {hiddenCount} films hidden</p>}
      {others.length > 0 && (
        <div className="chips-line">
          {others.map((o) => (
            <span key={o.key} className="chip">
              <span>{o.label}</span>
              <button type="button" className="chip__x" aria-label={o.aria} onClick={() => onChange({ ...criteria, ...o.clear })}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { fuzzyFind } from "@/lib/fuzzy";
import type { Criteria, TagCriterion, TagMode } from "@/lib/searchState";

export type Tag = { idx: number; tag: string };
type Props = {
  tags: Tag[];
  criteria: Criteria;
  onChange: (c: Criteria) => void;
  hiddenCount?: number;
  /** per exclusion ("genre:Horror", "tag:284"): how many films it hid in the current search */
  hiddenBy?: Record<string, number>;
  /** extra content at the bottom of the panel, e.g. a "Show results" button */
  children?: React.ReactNode;
};

const STARS = [1, 2, 3, 4, 5];
const MODES: { mode: TagMode; label: string; hint: string }[] = [
  { mode: "prefer", label: "Prefer", hint: "Ranks matching films higher" },
  { mode: "must", label: "Must", hint: "Only films with this tag" },
  { mode: "not", label: "Exclude", hint: "Hides films with this tag" },
];

export type FilterChip = { key: string; label: string; clear: Partial<Criteria>; aria: string };

/** The non-tag criteria as labelled chips (person, title, plot, availability, runtime, kind, years, rating, language). */
export function filterChips(criteria: Criteria): FilterChip[] {
  const others: FilterChip[] = [];
  if (criteria.person) others.push({ key: "person", label: `👤 ${criteria.person}`, clear: { person: null }, aria: `Remove person ${criteria.person}` });
  if (criteria.title) others.push({ key: "title", label: `🔤 “${criteria.title}”`, clear: { title: null }, aria: `Remove title ${criteria.title}` });
  if (criteria.plot_query) others.push({ key: "plot", label: `📖 “${criteria.plot_query}”`, clear: { plot_query: null }, aria: "Remove plot search" });
  if (criteria.availability === "stream") {
    const services = criteria.streaming_services ?? [];
    const label = services.length ? `📺 Streaming on ${services.join(" or ")}` : "📺 Streaming (DE)";
    others.push({ key: "stream", label, clear: { availability: "any", streaming_services: [] }, aria: "Remove streaming filter" });
  }
  if (criteria.availability === "cinema") others.push({ key: "cinema", label: "🎬 In cinemas", clear: { availability: "any" }, aria: "Remove cinema filter" });
  if (criteria.max_runtime_min) others.push({ key: "runtime", label: `< ${criteria.max_runtime_min} min`, clear: { max_runtime_min: null }, aria: "Remove runtime limit" });
  if (criteria.kind !== "any") others.push({ key: "kind", label: criteria.kind === "documentary" ? "Documentaries" : "Feature films", clear: { kind: "any" }, aria: "Remove kind filter" });
  if (criteria.year_from || criteria.year_to) others.push({ key: "year", label: `${criteria.year_from ?? "…"}–${criteria.year_to ?? "…"}`, clear: { year_from: null, year_to: null }, aria: "Remove year range" });
  if (criteria.min_rating != null) others.push({ key: "rating", label: `★ Rated ${criteria.min_rating}+`, clear: { min_rating: null }, aria: "Remove rating filter" });
  if (criteria.original_language) others.push({ key: "lang", label: `Language: ${criteria.original_language}`, clear: { original_language: null }, aria: "Remove language filter" });
  return others;
}

/** The visible search state as a labelled settings panel: one block per mood tag (stars for weight,
 *  prefer / must / exclude), then exclusions, people and filters. */
export default function SearchChips({ tags, criteria, onChange, hiddenCount = 0, hiddenBy, children }: Props) {
  const [picking, setPicking] = useState(false);
  const [query, setQuery] = useState("");
  const name = useMemo(() => new Map(tags.map((t) => [t.idx, t.tag])), [tags]);
  const used = new Set(criteria.tags.map((t) => t.idx));
  // typo-tolerant ("medival" finds "medieval"); only a click on a suggestion adds the tag
  const free = tags.filter((t) => !used.has(t.idx));
  const byName = new Map(free.map((t) => [t.tag, t]));
  const matches = fuzzyFind(query, free.map((t) => t.tag))
    .slice(0, 8)
    .map((n) => byName.get(n)!);

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
  const others = filterChips(criteria);

  // what an exclusion does in this search: "hides 3 films here", or that it changes nothing
  const effect = (key: string, what: string) => {
    const n = hiddenBy?.[key];
    if (n === undefined) return null;
    return (
      <span className={`crit__note ${n === 0 ? "crit__note--idle" : ""}`}>
        {n === 0 ? `none of these films are ${key.startsWith("person:") ? "with " : ""}${what}: changes nothing` : `hides ${n} film${n === 1 ? "" : "s"} here`}
      </span>
    );
  };

  const modeSwitch = (t: TagCriterion, label: string) => (
    <div className="crit__modes" role="group" aria-label={`Mode for ${label}`}>
      {MODES.map((m) => (
        <button
          key={m.mode}
          type="button"
          title={m.hint}
          aria-pressed={t.mode === m.mode}
          className={`crit__mode crit__mode--${m.mode}`}
          onClick={() => setTag(t.idx, { mode: m.mode })}
        >
          {m.label}
        </button>
      ))}
    </div>
  );

  const head = (label: string, idx: number, struck = false) => (
    <div className="crit__head">
      <span className="crit__name">{struck ? <s>{label}</s> : label}</span>
      <button type="button" className="crit__x" aria-label={`Remove ${label}`} title="Remove" onClick={() => removeTag(idx)}>
        ×
      </button>
    </div>
  );

  return (
    <section className="search-chips criteria-panel" aria-label="Search criteria">
      <h2 className="criteria-title">Your mood settings</h2>
      {mood.length === 0 && excluded.length === 0 && (
        <p className="criteria-empty">No mood tags yet. Chat with me or add one below.</p>
      )}
      {mood.length > 0 && (
        <ul className="criteria-list">
          {mood.map((t) => {
            const label = name.get(t.idx) ?? `tag ${t.idx}`;
            const stars = Math.round(t.weight / 2);
            return (
              <li key={t.idx} className={`crit chip chip--mood ${t.mode === "must" ? "crit--must chip--must" : ""}`}>
                {head(label, t.idx)}
                <div className="crit__row">
                  <span className="crit__label">Weight</span>
                  <span className="crit__stars">
                    {STARS.map((d) => (
                      <button
                        key={d}
                        type="button"
                        className={d <= stars ? "on" : ""}
                        aria-label={`Weight ${d} of 5 for ${label}`}
                        title={`Weight ${d} of 5`}
                        onClick={() => setTag(t.idx, { weight: d * 2 })}
                      >
                        ★
                      </button>
                    ))}
                  </span>
                </div>
                {modeSwitch(t, label)}
              </li>
            );
          })}
        </ul>
      )}
      <div className="chip-add">
        <button type="button" className="crit-add chip--add" aria-expanded={picking} onClick={() => setPicking((p) => !p)}>
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
            {query.trim() && matches.length === 0 && <span className="tag-picker__none">No mood tag like that</span>}
            {matches.map((t) => (
              <button key={t.idx} type="button" onClick={() => addTag(t.idx)}>
                {t.tag}
              </button>
            ))}
          </span>
        )}
      </div>
      {(excluded.length > 0 || criteria.exclude_genres.length > 0 || criteria.exclude_people.length > 0) && (
        <>
          <h3 className="chips-heading">Excluded</h3>
          <ul className="criteria-list">
            {excluded.map((t) => {
              const label = name.get(t.idx) ?? `tag ${t.idx}`;
              return (
                <li key={t.idx} className="crit chip chip--excluded">
                  {head(label, t.idx, true)}
                  {effect(`tag:${t.idx}`, label)}
                  {modeSwitch(t, label)}
                </li>
              );
            })}
            {criteria.exclude_genres.map((g) => (
              <li key={g} className="crit chip chip--excluded">
                <div className="crit__head">
                  <span className="crit__name">🚫 {g} (genre)</span>
                  <button
                    type="button"
                    className="crit__x"
                    aria-label={`Remove excluded genre ${g}`}
                    onClick={() => onChange({ ...criteria, exclude_genres: criteria.exclude_genres.filter((x) => x !== g) })}
                  >
                    ×
                  </button>
                </div>
                {effect(`genre:${g}`, g)}
              </li>
            ))}
            {criteria.exclude_people.map((p) => (
              <li key={p} className="crit chip chip--excluded">
                <div className="crit__head">
                  <span className="crit__name">
                    🚫 <s>{p}</s>
                  </span>
                  <button
                    type="button"
                    className="crit__x"
                    aria-label={`Remove excluded person ${p}`}
                    onClick={() => onChange({ ...criteria, exclude_people: criteria.exclude_people.filter((x) => x !== p) })}
                  >
                    ×
                  </button>
                </div>
                {effect(`person:${p}`, p)}
              </li>
            ))}
          </ul>
        </>
      )}
      {hiddenCount > 0 && <p className="chips-hidden">→ {hiddenCount} films hidden</p>}
      {others.length > 0 && (
        <>
          <h3 className="chips-heading">Filters</h3>
          <ul className="criteria-list">
            {others.map((o) => (
              <li key={o.key} className="crit chip">
                <div className="crit__head">
                  <span className="crit__name">{o.label}</span>
                  <button type="button" className="crit__x" aria-label={o.aria} onClick={() => onChange({ ...criteria, ...o.clear })}>
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      {children}
    </section>
  );
}

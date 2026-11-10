"use client";

import { filterChips, type Tag } from "@/components/search/SearchChips";
import type { Criteria } from "@/lib/searchState";

type Props = {
  tags: Tag[];
  criteria: Criteria;
  onChange: (c: Criteria) => void;
  hiddenCount?: number;
  open: boolean;
  onToggle: () => void;
};

/** The search in one line of small chips (results page), so the films come early. Weights and
 *  prefer / must / exclude are edited in the full panel behind "Edit moods & filters". */
export default function CompactCriteria({ tags, criteria, onChange, hiddenCount = 0, open, onToggle }: Props) {
  const name = new Map(tags.map((t) => [t.idx, t.tag]));
  const label = (idx: number) => name.get(idx) ?? `tag ${idx}`;
  const mood = criteria.tags.filter((t) => t.mode !== "not");
  const notTags = criteria.tags.filter((t) => t.mode === "not");
  const filters = filterChips(criteria);
  const removeTag = (idx: number) => onChange({ ...criteria, tags: criteria.tags.filter((t) => t.idx !== idx) });
  const empty = mood.length + notTags.length + criteria.exclude_genres.length + criteria.exclude_people.length + filters.length === 0;

  const x = (aria: string, clear: () => void) => (
    <button type="button" className="sb-chip__x" aria-label={aria} onClick={clear}>
      ×
    </button>
  );

  return (
    <section className="search-bar" aria-label="Your search">
      <h2 className="search-bar__title">Your search</h2>
      {empty ? (
        <span className="search-bar__empty">No moods or filters yet</span>
      ) : (
        <ul className="search-bar__chips">
          {mood.map((t) => {
            const stars = Math.round(t.weight / 2);
            return (
              <li key={t.idx} className={`sb-chip${t.mode === "must" ? " sb-chip--must" : ""}`}>
                {label(t.idx)}
                <span className="sb-chip__stars" role="img" aria-label={`weight ${stars} of 5`}>
                  {"★".repeat(stars)}
                </span>
                {t.mode === "must" && <em>must</em>}
                {x(`Remove ${label(t.idx)}`, () => removeTag(t.idx))}
              </li>
            );
          })}
          {notTags.map((t) => (
            <li key={t.idx} className="sb-chip sb-chip--excluded">
              <s>{label(t.idx)}</s>
              {x(`Remove ${label(t.idx)}`, () => removeTag(t.idx))}
            </li>
          ))}
          {criteria.exclude_genres.map((g) => (
            <li key={`g-${g}`} className="sb-chip sb-chip--excluded">
              <s>{g}</s>
              {x(`Remove excluded genre ${g}`, () => onChange({ ...criteria, exclude_genres: criteria.exclude_genres.filter((v) => v !== g) }))}
            </li>
          ))}
          {criteria.exclude_people.map((p) => (
            <li key={`p-${p}`} className="sb-chip sb-chip--excluded">
              without {p}
              {x(`Remove excluded person ${p}`, () => onChange({ ...criteria, exclude_people: criteria.exclude_people.filter((v) => v !== p) }))}
            </li>
          ))}
          {filters.map((f) => (
            <li key={f.key} className="sb-chip sb-chip--filter">
              {f.label}
              {x(f.aria, () => onChange({ ...criteria, ...f.clear }))}
            </li>
          ))}
        </ul>
      )}
      {hiddenCount > 0 && <span className="search-bar__hidden">{hiddenCount} films hidden</span>}
      <button type="button" className="results-toggle search-bar__edit" aria-expanded={open} onClick={onToggle}>
        {open ? "Close settings ▴" : "Edit moods & filters ▾"}
      </button>
    </section>
  );
}

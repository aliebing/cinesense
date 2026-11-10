"use client";

import { filterChips, type Tag } from "@/components/search/SearchChips";
import type { Criteria } from "@/lib/searchState";

type Props = {
  tags: Tag[];
  criteria: Criteria;
  onChange: (c: Criteria) => void;
  hiddenCount?: number;
  /** per exclusion ("genre:Horror", "tag:284", "person:X"): how many films it hid in the current search */
  hiddenBy?: Record<string, number>;
  /** at the end of the row, e.g. the advanced search toggle */
  children?: React.ReactNode;
};

/** Exclusions and filters of the search as one row of chips, each removed with ×; every exclusion says what it does
 *  in this search ("hides 3", or "changes nothing"). */
export default function ExclusionsBar({ tags, criteria, onChange, hiddenCount = 0, hiddenBy, children }: Props) {
  const name = new Map(tags.map((t) => [t.idx, t.tag]));
  const label = (idx: number) => name.get(idx) ?? `tag ${idx}`;
  const notTags = criteria.tags.filter((t) => t.mode === "not");
  const filters = filterChips(criteria);
  const empty = notTags.length + criteria.exclude_genres.length + criteria.exclude_people.length + filters.length === 0;

  const x = (aria: string, clear: () => void) => (
    <button type="button" className="sb-chip__x" aria-label={aria} onClick={clear}>
      ×
    </button>
  );
  const effect = (key: string) => {
    const n = hiddenBy?.[key];
    if (n === undefined) return null;
    return <span className={`sb-chip__note${n === 0 ? " is-idle" : ""}`}>{n === 0 ? "changes nothing here" : `hides ${n}`}</span>;
  };

  return (
    <section className="search-bar" aria-label="Filters">
      <h2 className="search-bar__title">Filters</h2>
      {empty ? (
        <span className="search-bar__empty">None</span>
      ) : (
        <ul className="search-bar__chips">
          {notTags.map((t) => (
            <li key={t.idx} className="sb-chip sb-chip--excluded">
              <s>{label(t.idx)}</s>
              {effect(`tag:${t.idx}`)}
              {x(`Remove ${label(t.idx)}`, () => onChange({ ...criteria, tags: criteria.tags.filter((v) => v.idx !== t.idx) }))}
            </li>
          ))}
          {criteria.exclude_genres.map((g) => (
            <li key={`g-${g}`} className="sb-chip sb-chip--excluded">
              <s>{g}</s> (genre)
              {effect(`genre:${g}`)}
              {x(`Remove excluded genre ${g}`, () => onChange({ ...criteria, exclude_genres: criteria.exclude_genres.filter((v) => v !== g) }))}
            </li>
          ))}
          {criteria.exclude_people.map((p) => (
            <li key={`p-${p}`} className="sb-chip sb-chip--excluded">
              without {p}
              {effect(`person:${p}`)}
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
      {hiddenCount > 0 && <span className="search-bar__hidden">{hiddenCount} films hidden in all</span>}
      {children && <span className="search-bar__end">{children}</span>}
    </section>
  );
}

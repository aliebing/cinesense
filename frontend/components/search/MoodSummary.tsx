import Link from "next/link";
import { filterChips, type Tag } from "@/components/search/SearchChips";
import type { Criteria } from "@/lib/searchState";

const STARS = [1, 2, 3, 4, 5];

/** The search state read-only, in the same panel look as SearchChips: the detail page shows what ranks its row
 *  (and what ⚡ / 😂 just added); changing it happens on the start and results pages. */
export default function MoodSummary({ tags, criteria, hiddenCount = 0 }: { tags: Tag[]; criteria: Criteria; hiddenCount?: number }) {
  const name = new Map(tags.map((t) => [t.idx, t.tag]));
  const label = (idx: number) => name.get(idx) ?? `tag ${idx}`;
  const mood = criteria.tags.filter((t) => t.mode !== "not");
  const excluded = [...criteria.tags.filter((t) => t.mode === "not").map((t) => label(t.idx)), ...criteria.exclude_genres.map((g) => `${g} (genre)`)];
  const filters = filterChips(criteria);
  const empty = mood.length === 0 && excluded.length === 0 && filters.length === 0;

  return (
    <section className="search-chips criteria-panel mood-summary" aria-label="Your mood settings">
      <h2 className="criteria-title">Your mood settings</h2>
      {empty && <p className="criteria-empty">No mood settings yet: the row shows what fits this world.</p>}
      {mood.length > 0 && (
        <ul className="criteria-list">
          {mood.map((t) => {
            const stars = Math.round(t.weight / 2);
            return (
              <li key={t.idx} className={`crit chip chip--mood ${t.mode === "must" ? "crit--must chip--must" : ""}`}>
                <div className="crit__head">
                  <span className="crit__name">{label(t.idx)}</span>
                  {t.mode === "must" && <span className="mood-summary__must">must</span>}
                </div>
                <span className="crit__stars mood-summary__stars" aria-label={`Weight ${stars} of 5`} title={`Weight ${stars} of 5`}>
                  {STARS.map((d) => (
                    <span key={d} aria-hidden="true" className={d <= stars ? "on" : ""}>
                      ★
                    </span>
                  ))}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {excluded.length > 0 && (
        <>
          <h3 className="chips-heading">Excluded</h3>
          <ul className="criteria-list">
            {excluded.map((x) => (
              <li key={x} className="crit chip chip--excluded">
                <span className="crit__name">
                  <s>{x}</s>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {hiddenCount > 0 && <p className="chips-hidden">→ {hiddenCount} films hidden</p>}
      {filters.length > 0 && (
        <>
          <h3 className="chips-heading">Filters</h3>
          <ul className="criteria-list">
            {filters.map((f) => (
              <li key={f.key} className="crit chip">
                <span className="crit__name">{f.label}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <Link href="/results" className="mood-summary__edit">
        Change in search →
      </Link>
    </section>
  );
}

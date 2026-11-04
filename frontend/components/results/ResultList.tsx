"use client";

import { useEffect, useState } from "react";
import RelatedRow, { LoadingBar } from "@/components/genre/RelatedRow";
import { search, type DiscoverResult, type Relaxation } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";
import type { Movie, RankedMovie } from "@/lib/types";

const LIMIT = 48; // the row runs through the best matches; the header gives the real total
const count = new Intl.NumberFormat("en-US");

type Props = {
  criteria: Criteria;
  onOpen: (m: Movie) => void;
  onMeta?: (meta: Omit<DiscoverResult, "items">) => void;
  onRelax?: (c: Criteria, label: string) => void; // a search that finds too little offers ways to widen it
  widened?: { from: Criteria; labels: string[] } | null; // the user widened the search: say so, mark what films miss
};

/** The best matches as one endless row at the bottom, like the genre page; the header gives the real number and
 *  never claims completeness, and every card says why it matches. */
export default function ResultList({ criteria, onOpen, onMeta, onRelax, widened }: Props) {
  const [items, setItems] = useState<RankedMovie[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [extended, setExtended] = useState(false);
  // the options belong to the search they were computed for; while the next one loads they are stale
  const [relaxFor, setRelaxFor] = useState<{ key: string; options: Relaxation[] }>({ key: "", options: [] });
  const [error, setError] = useState(false);
  const [shownKey, setShownKey] = useState<string | null>(null); // the search the shown results belong to
  const key = JSON.stringify(criteria);
  const fromKey = widened ? JSON.stringify(widened.from) : "";

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      const from = fromKey ? (JSON.parse(fromKey) as Criteria) : undefined;
      const r = await search(JSON.parse(key) as Criteria, 0, LIMIT, from);
      if (cancelled) return;
      if (!r.ok) {
        setShownKey(key);
        return setError(true);
      }
      setError(false);
      setShownKey(key);
      setItems(r.data.items);
      setTotal(r.data.total);
      setExtended(r.data.extended_used);
      setRelaxFor({ key, options: r.data.relaxations ?? [] });
      onMeta?.({
        total: r.data.total,
        hidden_by_exclusion: r.data.hidden_by_exclusion,
        extended_used: r.data.extended_used,
        corrected_person: r.data.corrected_person,
        corrected_title: r.data.corrected_title,
        hidden_by: r.data.hidden_by,
      });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [key, fromKey, onMeta]);

  const loading = shownKey !== key;
  if (error && !loading) return <p className="results-error">Couldn&apos;t load films</p>;
  if (total === null) return <LoadingBar />;
  const relaxations = relaxFor.key === key ? relaxFor.options : [];
  const widen =
    onRelax && relaxations.length > 0 ? (
      <div className="results-relax-bar">
        <span>{items.length ? `Only ${count.format(total)} films match every wish. More with:` : "Nothing matches every wish. Try:"}</span>
        {relaxations.map((o) => (
          <button key={o.id} type="button" className="results-relax" onClick={() => onRelax(o.criteria, o.label)}>
            {o.label} · {count.format(o.count)} films
          </button>
        ))}
      </div>
    ) : null;
  const note = widened?.labels.length ? (
    <p className="results-widened">Widened: {widened.labels.join("; ")} — films marked ≠ miss part of your wish</p>
  ) : null;
  // a person or title the widening never drops (it is the wish itself): if nothing is found, say which and
  // offer the search without it (a misspelt name is already matched fuzzily by the backend)
  const identity = criteria.person
    ? { text: `👤 ${criteria.person}`, what: "person", without: { ...criteria, person: null }, label: `without ${criteria.person}` }
    : criteria.title
      ? { text: `🔤 “${criteria.title}”`, what: "title", without: { ...criteria, title: null }, label: `without “${criteria.title}”` }
      : null;
  if (items.length === 0)
    return (
      <>
        {loading && <LoadingBar />}
        {identity && relaxFor.key === key ? (
          <div className="results-relax-bar">
            <span>Nothing found with {identity.text}</span>
            {onRelax && (
              <button type="button" className="results-relax" onClick={() => onRelax(identity.without, identity.label)}>
                Search without this {identity.what}
              </button>
            )}
          </div>
        ) : (
          <p className="results-head">No matches in the CineSense catalogue</p>
        )}
        {note}
        {widen}
      </>
    );
  const label = (
    <>
      {count.format(total)} matches in the CineSense catalogue
      {total > items.length && <span className="related-hint"> · the best {items.length}</span>}
      {extended && <span className="results-extended"> · includes titles just added from Wikidata</span>}
    </>
  );
  return (
    <>
      {note}
      {widen}
      <RelatedRow items={items} onSelect={onOpen} label={label} name="Results" showReasons busy={loading} />
    </>
  );
}

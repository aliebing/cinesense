"use client";

import { useEffect, useState } from "react";
import RelatedRow from "@/components/genre/RelatedRow";
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
  const [relaxations, setRelaxations] = useState<Relaxation[]>([]);
  const [error, setError] = useState(false);
  const key = JSON.stringify(criteria);
  const fromKey = widened ? JSON.stringify(widened.from) : "";

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      const from = fromKey ? (JSON.parse(fromKey) as Criteria) : undefined;
      const r = await search(JSON.parse(key) as Criteria, 0, LIMIT, from);
      if (cancelled) return;
      if (!r.ok) return setError(true);
      setError(false);
      setItems(r.data.items);
      setTotal(r.data.total);
      setExtended(r.data.extended_used);
      setRelaxations(r.data.relaxations ?? []);
      onMeta?.({ total: r.data.total, hidden_by_exclusion: r.data.hidden_by_exclusion, extended_used: r.data.extended_used });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [key, fromKey, onMeta]);

  if (error) return <p className="results-error">Couldn&apos;t load films</p>;
  if (total === null) return null;
  const widen =
    onRelax && relaxations.length > 0 ? (
      <div className="results-relax-bar">
        <span>Nothing matches every wish. Try:</span>
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
  if (items.length === 0)
    return (
      <>
        <p className="results-head">No matches in the CineSense catalogue</p>
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
      <RelatedRow items={items} onSelect={onOpen} label={label} name="Results" showReasons />
    </>
  );
}

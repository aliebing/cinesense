"use client";

import { useEffect, useState } from "react";
import RelatedRow from "@/components/genre/RelatedRow";
import { search, type DiscoverResult } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";
import type { Movie, RankedMovie } from "@/lib/types";

const LIMIT = 48; // the row runs through the best matches; the header gives the real total
const count = new Intl.NumberFormat("en-US");

type Props = { criteria: Criteria; onOpen: (m: Movie) => void; onMeta?: (meta: Omit<DiscoverResult, "items">) => void };

/** The best matches as one endless row at the bottom, like the genre page; the header gives the real number and
 *  never claims completeness, and every card says why it matches. */
export default function ResultList({ criteria, onOpen, onMeta }: Props) {
  const [items, setItems] = useState<RankedMovie[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [extended, setExtended] = useState(false);
  const [error, setError] = useState(false);
  const key = JSON.stringify(criteria);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      const r = await search(JSON.parse(key) as Criteria, 0, LIMIT);
      if (cancelled) return;
      if (!r.ok) return setError(true);
      setError(false);
      setItems(r.data.items);
      setTotal(r.data.total);
      setExtended(r.data.extended_used);
      onMeta?.({ total: r.data.total, hidden_by_exclusion: r.data.hidden_by_exclusion, extended_used: r.data.extended_used });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [key, onMeta]);

  if (error) return <p className="results-error">Couldn&apos;t load films</p>;
  if (total === null) return null;
  if (items.length === 0) return <p className="results-head">No matches in the CineSense catalogue</p>;
  const label = (
    <>
      {count.format(total)} matches in the CineSense catalogue
      {total > items.length && <span className="related-hint"> · the best {items.length}</span>}
      {extended && <span className="results-extended"> · includes titles just added from Wikidata</span>}
    </>
  );
  return <RelatedRow items={items} onSelect={onOpen} label={label} name="Results" showReasons />;
}

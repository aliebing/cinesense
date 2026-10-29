"use client";

import { useEffect, useState } from "react";
import HoverTrailer from "@/components/media/HoverTrailer";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { search, type DiscoverResult } from "@/lib/api";
import type { Criteria } from "@/lib/searchState";
import type { Movie, RankedMovie } from "@/lib/types";

const PAGE = 20;
const count = new Intl.NumberFormat("en-US");

type Props = { criteria: Criteria; onOpen: (m: Movie) => void; onMeta?: (meta: Omit<DiscoverResult, "items">) => void };

/** Paged grid of results; the header gives the real number and never claims completeness. */
export default function ResultList({ criteria, onOpen, onMeta }: Props) {
  const [items, setItems] = useState<RankedMovie[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [extended, setExtended] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const key = JSON.stringify(criteria);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      setLoading(true);
      const r = await search(JSON.parse(key) as Criteria, 0, PAGE);
      if (cancelled) return;
      setLoading(false);
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

  const loadMore = async () => {
    setLoading(true);
    const r = await search(criteria, items.length, PAGE);
    setLoading(false);
    if (r.ok) setItems((prev) => [...prev, ...r.data.items.filter((i) => !prev.some((p) => p.movie.id === i.movie.id))]);
  };

  if (error) return <p className="results-error">Couldn&apos;t load films</p>;
  return (
    <section className="results" aria-label="Results">
      {total !== null && (
        <h2 className="results-head">
          {count.format(total)} matches in the CineSense catalogue
          {extended && <span className="results-extended"> · includes titles just added from Wikidata</span>}
        </h2>
      )}
      <div className="results-grid">
        {items.map((r) => (
          <article key={r.movie.id} className="result-card" data-testid="result-card">
            <HoverTrailer movie={r.movie} className="result-poster">
              <button type="button" className="result-open" aria-label={`Open ${r.movie.title}`} onClick={() => onOpen(r.movie)}>
                <ImageOrPlaceholder src={r.movie.poster_url} alt="" />
                <i className="result-match">{r.match_percent}%</i>
              </button>
            </HoverTrailer>
            <h3>{r.movie.title}</h3>
            <p className="result-meta">
              {[r.movie.year, r.movie.kind === "documentary" ? "Documentary" : null, r.movie.ml_rating !== null ? `⭐ ${r.movie.ml_rating.toFixed(1)} (${count.format(r.movie.ml_rating_count)})` : null]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {r.reasons.length > 0 && <p className="result-why">{r.reasons.join(" · ")}</p>}
          </article>
        ))}
      </div>
      {total !== null && items.length < total && (
        <button type="button" className="results-more" onClick={loadMore} disabled={loading}>
          Load more
        </button>
      )}
    </section>
  );
}

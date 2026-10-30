"use client";

import { useState, type CSSProperties } from "react";
import HoverTrailer from "@/components/media/HoverTrailer";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import type { Movie, RankedMovie } from "@/lib/types";

export const PAGE_SIZE = 6;

/** Page after `page` (or before it for step -1), wrapping around at both ends. */
export function turnPage(page: number, step: 1 | -1, pages: number): number {
  return pages > 0 ? (page + step + pages) % pages : 0;
}

/** A few matching films at a time; the gold » slides a completely new set in. Hovering a card plays its trailer. */
export default function RelatedRow({ items, onSelect }: { items: RankedMovie[]; onSelect: (m: Movie) => void }) {
  const [page, setPage] = useState(0);
  const pages = Math.ceil(items.length / PAGE_SIZE);
  const listKey = `${items[0]?.movie.id}:${items.length}`;
  const [seenKey, setSeenKey] = useState(listKey);
  if (seenKey !== listKey) {
    // a new list starts at its first page
    setSeenKey(listKey);
    setPage(0);
  }

  if (items.length === 0) return null;
  const current = Math.min(page, pages - 1);
  return (
    <section className="related" aria-label="Also fits your mood">
      <h3 className="related-label">
        Also fits your mood
        {pages > 1 && (
          <span className="related-count">
            {current + 1} / {pages}
          </span>
        )}
      </h3>
      <div className="related-carousel">
        {pages > 1 && (
          <button type="button" className="related-nav related-nav--prev" aria-label="Previous films" onClick={() => setPage(turnPage(current, -1, pages))}>
            «
          </button>
        )}
        <div className="related-viewport">
          <div className="related-track" style={{ "--page": current } as CSSProperties}>
            {items.map((r, i) => {
              const visible = Math.floor(i / PAGE_SIZE) === current;
              return (
                <HoverTrailer key={r.movie.id} movie={r.movie} className="related-wrap">
                  <button
                    type="button"
                    className="related-card"
                    aria-label={`${r.movie.title}, ${r.match_percent}% match`}
                    tabIndex={visible ? 0 : -1}
                    aria-hidden={visible ? undefined : true}
                    onClick={() => onSelect(r.movie)}
                  >
                    <ImageOrPlaceholder src={r.movie.poster_url} alt="" />
                    <i>{r.match_percent}%</i>
                    <span>{r.movie.title}</span>
                  </button>
                </HoverTrailer>
              );
            })}
          </div>
        </div>
        {pages > 1 && (
          <button type="button" className="related-nav related-nav--next" aria-label="Next films" onClick={() => setPage(turnPage(current, 1, pages))}>
            »
          </button>
        )}
      </div>
    </section>
  );
}

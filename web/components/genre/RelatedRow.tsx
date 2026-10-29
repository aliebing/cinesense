"use client";

import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import type { Movie, RankedMovie } from "@/lib/types";

/** Slowly drifting row of matching films; hovering pauses it (CSS animation). */
export default function RelatedRow({ items, onSelect }: { items: RankedMovie[]; onSelect: (m: Movie) => void }) {
  if (items.length === 0) return null;
  return (
    <section className="related" aria-label="Also fits your mood">
      <h3 className="related-label">Also fits your mood</h3>
      <div className="related-viewport">
        <div className="related-track">
          {[...items, ...items].map((r, i) => (
            <button
              key={`${r.movie.id}-${i}`}
              type="button"
              className="related-card"
              aria-label={`${r.movie.title}, ${r.match_percent}% match`}
              tabIndex={i < items.length ? 0 : -1}
              aria-hidden={i < items.length ? undefined : true}
              onClick={() => onSelect(r.movie)}
            >
              <ImageOrPlaceholder src={r.movie.poster_url} alt="" />
              <i>{r.match_percent}%</i>
              <span>{r.movie.title}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

"use client";

import { MATCH_HINT } from "@/components/genre/RelatedRow";
import HoverTrailer from "@/components/media/HoverTrailer";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { whyText } from "@/lib/why";
import type { Movie, RankedMovie } from "@/lib/types";

type Props = {
  items: RankedMovie[];
  onSelect: (m: Movie) => void;
  label: React.ReactNode;
  /** the streaming filter is on: films whose streaming was not looked up yet say so */
  streamCheck?: boolean;
  busy?: boolean;
  /** the grid of every further match uses the same cards: its own name and class */
  name?: string;
  className?: string;
};

/** The few best matches in front: large posters standing still, each with why it fits written out below. */
export default function BestMatches({ items, onSelect, label, streamCheck = false, busy = false, name = "Best matches", className = "" }: Props) {
  return (
    <section className={`best${className ? ` ${className}` : ""}${busy ? " is-busy" : ""}`} aria-label={name} aria-busy={busy}>
      <h3 className="related-label">{label}</h3>
      <ol className="best-list">
        {items.map((r) => (
          <li key={r.movie.id} className="best-item">
            <HoverTrailer movie={r.movie} className="related-wrap best-wrap">
              <button type="button" className="related-card best-card" aria-label={`${r.movie.title}, ${r.match_percent}% match`} onClick={() => onSelect(r.movie)}>
                <ImageOrPlaceholder src={r.movie.poster_url} alt="" />
                <i title={MATCH_HINT}>{r.match_percent}% match</i>
              </button>
            </HoverTrailer>
            <p className="best-title">
              {r.movie.title}
              {r.movie.year ? <span> ({r.movie.year})</span> : null}
            </p>
            {r.reasons.length > 0 && <p className="best-why">{whyText(r.reasons)}</p>}
            {streamCheck && r.movie.availability.streaming_de === null && <small className="result-unchecked">? streaming not checked</small>}
            {r.misses?.map((m) => (
              <small key={m} className="result-miss">
                ≠ {m}
              </small>
            ))}
          </li>
        ))}
      </ol>
    </section>
  );
}

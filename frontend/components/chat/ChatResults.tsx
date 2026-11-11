"use client";

import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import type { Movie, RankedMovie } from "@/lib/types";

/** The agent's picks (3-5) under its reply: click opens the stage (no hover trailer here:
 *  trailers play only in the search results and on the film stage). */
export default function ChatResults({
  results,
  onOpen,
  stale = false,
}: {
  results: RankedMovie[];
  onOpen: (m: Movie) => void;
  /** the settings changed since this reply: its picks belong to the earlier search and no longer open */
  stale?: boolean;
}) {
  return (
    <div className={`chat-picks${stale ? " chat-picks--stale" : ""}`}>
      {stale && <p className="chat-picks__stale">Your settings changed since: these picks were for the earlier search.</p>}
      {results.map((r) => (
        <article key={r.movie.id} className="chat-pick" data-testid="chat-pick">
          <div className="chat-pick-media">
            <button type="button" aria-label={`Open ${r.movie.title}`} disabled={stale} onClick={() => onOpen(r.movie)}>
              <ImageOrPlaceholder src={r.movie.horizontal_poster_url ?? r.movie.backdrop_url ?? r.movie.poster_url} alt="" />
            </button>
          </div>
          <div className="chat-pick-text">
            <strong>
              {r.movie.title}
              {r.movie.year ? ` (${r.movie.year})` : ""}
            </strong>
            {r.reasons.length > 0 && <span>{r.reasons.slice(0, 2).join(" · ")}</span>}
            {r.misses?.map((m) => (
              <small key={m} className="result-miss">
                ≠ {m}
              </small>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

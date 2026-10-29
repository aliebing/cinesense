"use client";

import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import HoverTrailer from "@/components/media/HoverTrailer";
import type { Movie, RankedMovie } from "@/lib/types";

/** The agent's top 3 picks under its reply: hover plays the trailer, click opens the stage. */
export default function ChatResults({ results, onOpen }: { results: RankedMovie[]; onOpen: (m: Movie) => void }) {
  return (
    <div className="chat-picks">
      {results.slice(0, 3).map((r) => (
        <article key={r.movie.id} className="chat-pick" data-testid="chat-pick">
          <HoverTrailer movie={r.movie} className="chat-pick-media">
            <button type="button" aria-label={`Open ${r.movie.title}`} onClick={() => onOpen(r.movie)}>
              <ImageOrPlaceholder src={r.movie.horizontal_poster_url ?? r.movie.backdrop_url ?? r.movie.poster_url} alt="" />
            </button>
          </HoverTrailer>
          <div className="chat-pick-text">
            <strong>
              {r.movie.title}
              {r.movie.year ? ` (${r.movie.year})` : ""}
            </strong>
            {r.reasons.length > 0 && <span>{r.reasons.slice(0, 2).join(" · ")}</span>}
          </div>
        </article>
      ))}
    </div>
  );
}

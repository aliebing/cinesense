"use client";

import { useState } from "react";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import type { MoodWorld, Movie } from "@/lib/types";

const FEEDBACK = ["👍 More like this", "⚡ More action", "😂 Funnier", "👎 Not for me"];
const rating = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function metaLine(m: Movie): string {
  const parts = [
    m.year ? String(m.year) : null,
    m.runtime_min ? `${Math.floor(m.runtime_min / 60)} h ${m.runtime_min % 60} min` : null,
    `${m.original_language.toUpperCase()} (original)`,
    m.age_rating_de ? `FSK ${m.age_rating_de}` : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

function Trailer({ movie }: { movie: Movie }) {
  const [playing, setPlaying] = useState(false);
  const key = movie.youtube_key;
  if (key && key !== "placeholder" && playing) {
    return (
      <iframe
        className="stage-trailer__frame"
        src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(key)}?autoplay=1`}
        title={`Official trailer: ${movie.title}`}
        allow="autoplay; encrypted-media; picture-in-picture"
        allowFullScreen
      />
    );
  }
  return (
    <>
      <ImageOrPlaceholder src={movie.backdrop_url} alt="" />
      {key && key !== "placeholder" ? (
        <button type="button" className="stage-trailer__play" onClick={() => setPlaying(true)} aria-label="Play trailer">
          <b aria-hidden="true">▶</b>
        </button>
      ) : null}
      <small className="stage-trailer__note">
        {key === "placeholder" ? "Placeholder trailer" : key ? "Official trailer (YouTube)" : "No official trailer available"}
      </small>
    </>
  );
}

/** Cinema stage: poster, trailer, info and feedback (spec §5, layout B). */
export default function StagePanel({ movie, world, why }: { movie: Movie; world: MoodWorld; why: string }) {
  const { in_cinema_de, streaming_flatrate_de } = movie.availability;
  return (
    <section className="stage" aria-label={`On stage: ${movie.title}`}>
      <div className="stage-poster">
        <ImageOrPlaceholder src={movie.poster_url} alt={`Poster: ${movie.title}`} />
      </div>
      <div className="stage-trailer" key={movie.id}>
        <Trailer movie={movie} />
      </div>
      <div className="stage-info">
        <div className="stage-kicker">{movie.genres.join(" · ") || world.title}</div>
        <h2>{movie.title}</h2>
        <p className="stage-meta">{metaLine(movie)}</p>
        <div className="stage-tags">
          {movie.is_placeholder && <span className="stage-tag--placeholder">Placeholder</span>}
          {in_cinema_de && <span>🎬 In cinemas</span>}
          {streaming_flatrate_de.length > 0 && <span>📺 Streaming on {streaming_flatrate_de.join(", ")}</span>}
          {movie.vote_average !== null && <span>⭐ TMDB {rating.format(movie.vote_average)}</span>}
        </div>
        <div className="stage-why">
          <b>Why it fits you:</b> <span>{why}</span>
        </div>
        <div className="stage-feedback">
          {FEEDBACK.map((f) => (
            <button key={f} type="button" disabled title="Coming with personalisation">
              {f}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

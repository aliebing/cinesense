"use client";

import { useState } from "react";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import type { MoodWorld, Movie } from "@/lib/types";

const FEEDBACK = ["👍 Mehr davon", "⚡ Mehr Action", "😂 Lustiger", "👎 Nicht mein Ding"];
const rating = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function metaLine(m: Movie): string {
  const parts = [
    m.year ? String(m.year) : null,
    m.runtime_min ? `${Math.floor(m.runtime_min / 60)} h ${m.runtime_min % 60} min` : null,
    `${m.original_language.toUpperCase()} (OV)`,
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
        title={`Offizieller Trailer: ${movie.title}`}
        allow="autoplay; encrypted-media; picture-in-picture"
        allowFullScreen
      />
    );
  }
  return (
    <>
      <ImageOrPlaceholder src={movie.backdrop_url} alt="" />
      {key && key !== "placeholder" ? (
        <button type="button" className="stage-trailer__play" onClick={() => setPlaying(true)} aria-label="Trailer abspielen">
          <b aria-hidden="true">▶</b>
        </button>
      ) : null}
      <small className="stage-trailer__note">
        {key === "placeholder" ? "Platzhalter-Trailer" : key ? "Offizieller Trailer (YouTube)" : "Kein offizieller Trailer verfügbar"}
      </small>
    </>
  );
}

/** Cinema stage: poster, trailer, info and feedback (spec §5, layout B). */
export default function StagePanel({ movie, world, why }: { movie: Movie; world: MoodWorld; why: string }) {
  const { in_cinema_de, streaming_flatrate_de } = movie.availability;
  return (
    <section className="stage" aria-label={`Auf der Bühne: ${movie.title}`}>
      <div className="stage-poster">
        <ImageOrPlaceholder src={movie.poster_url} alt={`Poster: ${movie.title}`} />
      </div>
      <div className="stage-trailer" key={movie.id}>
        <Trailer movie={movie} />
      </div>
      <div className="stage-info">
        <div className="stage-kicker">{movie.genres.join(" · ") || world.title_de}</div>
        <h2>{movie.title}</h2>
        <p className="stage-meta">{metaLine(movie)}</p>
        <div className="stage-tags">
          {movie.is_placeholder && <span className="stage-tag--placeholder">Platzhalter</span>}
          {in_cinema_de && <span>🎬 Im Kino</span>}
          {streaming_flatrate_de.length > 0 && <span>📺 Im Stream bei {streaming_flatrate_de.join(", ")}</span>}
          {movie.vote_average !== null && <span>⭐ TMDB {rating.format(movie.vote_average)}</span>}
        </div>
        <div className="stage-why">
          <b>Warum für dich:</b> <span>{why}</span>
        </div>
        <div className="stage-feedback">
          {FEEDBACK.map((f) => (
            <button key={f} type="button" disabled title="Folgt mit der Personalisierung">
              {f}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

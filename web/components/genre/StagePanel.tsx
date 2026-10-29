"use client";

import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { useRef } from "react";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { embedUrl, listenTo, useYouTubeState } from "@/lib/youtubePlayer";
import type { MoodWorld, Movie } from "@/lib/types";

const rating = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const count = new Intl.NumberFormat("en-US");

function metaLine(m: Movie): string {
  const parts = [
    m.year ? String(m.year) : null,
    m.runtime_min ? `${Math.floor(m.runtime_min / 60)} h ${m.runtime_min % 60} min` : null,
    m.original_language ? `${m.original_language.toUpperCase()} (original)` : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

function Trailer({ movie }: { movie: Movie }) {
  // shares the app-wide "one trailer at a time" store with the hover trailers
  const stageId = `stage-${movie.id}`;
  const { activeId, activate } = useActiveTrailer();
  const playing = activeId === stageId;
  const setPlaying = (on: boolean) => on && activate(stageId);
  const frame = useRef<HTMLIFrameElement | null>(null);
  const raw = movie.youtube_key && movie.youtube_key !== "placeholder" ? movie.youtube_key : null;
  const { failed } = useYouTubeState(playing, raw, frame, stageId);
  const key = movie.youtube_key;
  if (raw && playing && !failed) {
    return (
      <iframe
        ref={frame}
        onLoad={() => listenTo(frame, stageId)}
        className="stage-trailer__frame"
        src={embedUrl(raw, "autoplay=1")}
        title={`Official trailer: ${movie.title}`}
        allow="autoplay; encrypted-media; picture-in-picture"
        allowFullScreen
      />
    );
  }
  if (raw && failed) {
    return (
      <>
        <ImageOrPlaceholder src={movie.backdrop_url} alt="" />
        <small className="stage-trailer__note">
          This trailer can&apos;t be played here (blocked for other sites or in Germany).{" "}
          <a href={`https://www.youtube.com/watch?v=${encodeURIComponent(raw)}`} target="_blank" rel="noreferrer">
            Watch on YouTube
          </a>
        </small>
      </>
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

function Streaming({ movie }: { movie: Movie }) {
  const options = movie.availability.streaming_de;
  if (options === null) return <span className="stage-tag--muted">Streaming availability unknown</span>;
  if (options.length === 0) return <span className="stage-tag--muted">Not streaming in Germany</span>;
  const subs = movie.availability.subscription_services;
  const others = new Set(options.filter((o) => o.type !== "subscription").map((o) => o.service));
  return (
    <>
      {subs.map((s) => (
        <span key={s}>📺 {s}</span>
      ))}
      {others.size > 0 && <span className="stage-tag--muted">+ rent/buy on {others.size} services</span>}
    </>
  );
}

/** Cinema stage: poster, trailer, info and feedback (spec §5, layout B). */
type Props = {
  movie: Movie;
  world: MoodWorld;
  why: string;
  /** current 👍/👎 for this film: 1, -1 or 0 */
  feedback?: number;
  onFeedback?: (value: -1 | 0 | 1) => void;
  onSteer?: (kind: "action" | "funny") => void;
};

export default function StagePanel({ movie, world, why, feedback = 0, onFeedback, onSteer }: Props) {
  const people = [
    movie.directors.length ? `Directed by ${movie.directors.slice(0, 2).join(", ")}` : null,
    movie.cast_top.length ? `with ${movie.cast_top.slice(0, 3).join(", ")}` : null,
  ].filter(Boolean);
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
        {people.length > 0 && <p className="stage-people">{people.join(" · ")}</p>}
        <div className="stage-tags">
          {movie.is_placeholder && <span className="stage-tag--placeholder">Placeholder</span>}
          {movie.availability.in_cinema_de && (
            <span>🎬 In cinemas{movie.release_date_de ? ` (German release ${movie.release_date_de})` : ""}</span>
          )}
          <Streaming movie={movie} />
          {movie.ml_rating !== null && (
            <span>
              ⭐ MovieLens {rating.format(movie.ml_rating)}/5 ({count.format(movie.ml_rating_count)} ratings)
            </span>
          )}
        </div>
        {movie.top_tags.length > 0 && (
          <div className="stage-tags stage-tags--mood">
            {movie.top_tags.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        )}
        <div className="stage-links">
          {movie.imdb_id && (
            <a href={`https://www.imdb.com/title/${movie.imdb_id}/`} target="_blank" rel="noreferrer">
              IMDb
            </a>
          )}
          {movie.wikipedia_title && (
            <a href={`https://en.wikipedia.org/wiki/${encodeURIComponent(movie.wikipedia_title.replaceAll(" ", "_")).replace(/%28/g, "(").replace(/%29/g, ")")}`} target="_blank" rel="noreferrer">
              Wikipedia
            </a>
          )}
        </div>
        <div className="stage-why">
          <b>Why it fits you:</b> <span>{why}</span>
        </div>
        <div className="stage-feedback">
          <button
            type="button"
            aria-pressed={feedback === 1}
            className={feedback === 1 ? "is-on" : ""}
            disabled={!onFeedback}
            onClick={() => onFeedback?.(feedback === 1 ? 0 : 1)}
          >
            👍 More like this
          </button>
          <button type="button" disabled={!onSteer} title="Only for this session" onClick={() => onSteer?.("action")}>
            ⚡ More action
          </button>
          <button type="button" disabled={!onSteer} title="Only for this session" onClick={() => onSteer?.("funny")}>
            😂 Funnier
          </button>
          <button
            type="button"
            aria-pressed={feedback === -1}
            className={feedback === -1 ? "is-on is-off" : ""}
            disabled={!onFeedback}
            onClick={() => onFeedback?.(feedback === -1 ? 0 : -1)}
          >
            👎 Not for me
          </button>
        </div>
      </div>
    </section>
  );
}

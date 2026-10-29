"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { embedUrl, isBadTrailer, listenTo, useYouTubeState } from "@/lib/youtubePlayer";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { Movie } from "@/lib/types";

const INTENT_MS = 500;
function embedSrc(key: string, muted: boolean) {
  const k = encodeURIComponent(key);
  return embedUrl(key, `autoplay=1&mute=${muted ? 1 : 0}&controls=0&loop=1&playlist=${k}&modestbranding=1&playsinline=1&rel=0`);
}

/** Wraps a tile/card: hovering for 0.5 s starts the trailer muted inside it; one trailer app-wide.
 *  The player stays invisible until YouTube reports playback; if it reports an error the tile keeps its image,
 *  the id is reported to the backend and never offered again. */
export default function HoverTrailer({ movie, children, className = "" }: { movie: Movie; children: ReactNode; className?: string }) {
  const id = useId();
  const { activeId, activate, deactivate } = useActiveTrailer();
  const reduced = useReducedMotion();
  const [muted, setMuted] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const frame = useRef<HTMLIFrameElement | null>(null);
  const active = activeId === id;
  const candidate = movie.youtube_key && !isBadTrailer(movie.youtube_key) ? movie.youtube_key : null;
  const { playing, failed } = useYouTubeState(active, candidate);
  const key = failed ? null : candidate;

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
    deactivate(id);
  }, [id, deactivate]);

  const onEnter = () => {
    if (reduced) return;
    if (timer.current) clearTimeout(timer.current); // one pending start at a time
    timer.current = setTimeout(() => {
      setMuted(true);
      activate(id);
    }, INTENT_MS);
  };
  const onLeave = () => {
    if (timer.current) clearTimeout(timer.current);
    deactivate(id);
  };
  const listen = () => listenTo(frame, id);

  return (
    <div
      className={`hover-trailer ${active ? "is-active" : ""} ${className}`}
      data-testid="hover-trailer"
      onPointerEnter={onEnter}
      onPointerLeave={onLeave}
    >
      {children}
      {active && key && (
        <div className={`hover-trailer__player ${playing ? "is-playing" : ""}`}>
          <iframe
            ref={frame}
            onLoad={listen}
            src={embedSrc(key, muted)}
            title={`Trailer: ${movie.title}`}
            allow="autoplay; encrypted-media; picture-in-picture"
          />
          <button
            type="button"
            className="hover-trailer__sound"
            aria-label={muted ? "Unmute trailer" : "Mute trailer"}
            onClick={(e) => {
              e.stopPropagation();
              setMuted((m) => !m);
            }}
          >
            {muted ? "🔇" : "🔊"}
          </button>
        </div>
      )}
      {active && !movie.youtube_key && <span className="hover-trailer__note">No trailer available</span>}
      {reduced && key && !active && (
        <button
          type="button"
          className="hover-trailer__play"
          aria-label="Play trailer"
          onClick={(e) => {
            e.stopPropagation();
            activate(id);
          }}
        >
          ▶
        </button>
      )}
    </div>
  );
}

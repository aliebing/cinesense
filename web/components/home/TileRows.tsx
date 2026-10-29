"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import HoverTrailer from "@/components/media/HoverTrailer";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { MoodWorld, Movie, TileRow } from "@/lib/types";

type Props = { rows: TileRow[]; onSelect: (m: Movie) => void; variedSpeed: boolean };

const EVEN_SPEED = 0.9;
const VARIED_SPEEDS = [0.75, 1.2, 0.63, 1.0];

/** The worlds shown in the rows: the active (hero) world first, then the next ones, wrapping. */
export function visibleWorlds(active: number, worlds: MoodWorld[], count = 4): MoodWorld[] {
  if (worlds.length === 0) return [];
  return Array.from({ length: Math.min(count, worlds.length) }, (_, i) => worlds[(active + i) % worlds.length]);
}

function TileImage({ movie }: { movie: Movie }) {
  const [failed, setFailed] = useState(false);
  const src = movie.horizontal_poster_url ?? movie.backdrop_url;
  if (!src || failed) {
    return (
      <span className="title-card" data-testid="title-card">
        {movie.title}
      </span>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element -- external poster CDN, sized by CSS
  return <img className="img-cover" src={src} alt="" draggable={false} onError={() => setFailed(true)} />;
}

/** One row per mood world; neighbouring rows run in opposite directions in seamless loops (spec §4). */
export default function TileRows({ rows, onSelect, variedSpeed }: Props) {
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [paused, setPaused] = useState(false);
  const reduced = useReducedMotion();
  const { activeId } = useActiveTrailer();
  const pausedRef = useRef(paused);
  const variedRef = useRef(variedSpeed);
  useEffect(() => {
    pausedRef.current = paused || activeId !== null; // a playing trailer must not slide away
    variedRef.current = variedSpeed;
  }, [paused, variedSpeed, activeId]);

  useEffect(() => {
    if (reduced) return;
    const offsets = rowRefs.current.map((_, i) => -i * 37);
    let frame = 0;
    const step = () => {
      rowRefs.current.forEach((el, i) => {
        if (!el) return;
        const half = el.scrollWidth / 2;
        if (!pausedRef.current) {
          const speed = variedRef.current ? VARIED_SPEEDS[i % VARIED_SPEEDS.length] : EVEN_SPEED;
          offsets[i] += (i % 2 ? 1 : -1) * speed;
        }
        if (half > 0) {
          if (offsets[i] <= -half) offsets[i] += half;
          if (offsets[i] > 0) offsets[i] -= half;
        }
        el.style.transform = `translateX(${offsets[i]}px)`;
      });
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [reduced, rows.length]);

  return (
    <div className="tile-rows" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      {rows.map(({ world, movies }, r) => (
        <div key={world.id} className="tile-row-wrap">
          <Link href={`/world/${world.id}`} className="tile-row-label" style={{ ["--tint" as string]: world.tint }}>
            {world.title}
          </Link>
          <div className="tile-row-viewport">
          <div
            className="tile-row"
            data-testid="tile-row"
            ref={(el) => {
              rowRefs.current[r] = el;
            }}
          >
            {[...movies, ...movies].map((m, i) => (
              <HoverTrailer key={`${m.id}-${i}`} movie={m} className="tile-wrap">
                <button
                  type="button"
                  className="tile"
                  aria-label={m.title}
                  tabIndex={i < movies.length ? 0 : -1}
                  aria-hidden={i < movies.length ? undefined : true}
                  onClick={() => onSelect(m)}
                >
                  <TileImage movie={m} />
                </button>
              </HoverTrailer>
            ))}
          </div>
          </div>
        </div>
      ))}
    </div>
  );
}

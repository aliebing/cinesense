"use client";

import { useEffect, useRef, useState } from "react";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { Movie } from "@/lib/types";

type Props = { movies: Movie[]; rows: number; onSelect: (m: Movie) => void; variedSpeed: boolean };

const EVEN_SPEED = 0.35;
const VARIED_SPEEDS = [0.3, 0.48, 0.24, 0.4];

function splitIntoRows(movies: Movie[], rows: number): Movie[][] {
  const out: Movie[][] = Array.from({ length: rows }, () => []);
  movies.forEach((m, i) => out[i % rows].push(m));
  return out;
}

/** Flat tile rows; neighbouring rows run in opposite directions in seamless loops (spec §4). */
export default function TileRows({ movies, rows, onSelect, variedSpeed }: Props) {
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [paused, setPaused] = useState(false);
  const reduced = useReducedMotion();
  const pausedRef = useRef(paused);
  const variedRef = useRef(variedSpeed);
  useEffect(() => {
    pausedRef.current = paused;
    variedRef.current = variedSpeed;
  }, [paused, variedSpeed]);

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
  }, [reduced, rows]);

  return (
    <div className="tile-rows" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      {splitIntoRows(movies, rows).map((rowMovies, r) => (
        <div
          key={r}
          className="tile-row"
          data-testid="tile-row"
          ref={(el) => {
            rowRefs.current[r] = el;
          }}
        >
          {[...rowMovies, ...rowMovies].map((m, i) => (
            <button
              key={`${m.id}-${i}`}
              type="button"
              className="tile"
              aria-label={m.title}
              tabIndex={i < rowMovies.length ? 0 : -1}
              aria-hidden={i < rowMovies.length ? undefined : true}
              onClick={() => onSelect(m)}
            >
              <ImageOrPlaceholder src={m.backdrop_url ?? m.poster_url} alt="" />
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

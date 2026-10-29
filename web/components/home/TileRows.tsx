"use client";

import { useEffect, useRef, useState } from "react";
import HoverTrailer from "@/components/media/HoverTrailer";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { MoodWorld, Movie, TileRow } from "@/lib/types";

type Props = { rows: TileRow[]; onSelect: (m: Movie) => void; variedSpeed: boolean };

const EVEN_SPEED = 54; // px per second
const VARIED_SPEEDS = [45, 72, 38, 60];
const TRAILER_FACTOR = 0.3; // rows keep gliding slowly while a trailer plays
const EASE_MS = 600; // time constant for speed changes

/** Moves an offset and wraps it into (-period, 0] — exactly one loop period, so the seam never jumps. */
export function advance(offset: number, delta: number, period: number): number {
  let next = offset + delta;
  if (period > 0) {
    while (next <= -period) next += period;
    while (next > 0) next -= period;
  }
  return next;
}

/** Exponential easing of the speed factor towards its target (frame-rate independent). */
export function easeSpeed(current: number, target: number, dtMs: number): number {
  return target + (current - target) * Math.exp(-dtMs / EASE_MS);
}

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
  // state per world (not per row slot): rows reorder when the hero world changes and must not jump
  const rowEls = useRef(new Map<string, HTMLDivElement>());
  const offsets = useRef(new Map<string, number>());
  const directions = useRef(new Map<string, number>());
  const reduced = useReducedMotion();
  const { activeId } = useActiveTrailer();
  const slowRef = useRef(false);
  const variedRef = useRef(variedSpeed);
  const orderRef = useRef<string[]>([]);
  useEffect(() => {
    slowRef.current = activeId !== null; // a playing trailer must not slide away from under the pointer
    variedRef.current = variedSpeed;
  }, [variedSpeed, activeId]);
  useEffect(() => {
    orderRef.current = rows.map((r) => r.world.id);
    for (const id of orderRef.current) {
      // neighbouring worlds run in opposite directions; fixed per world, so it never flips mid-run
      if (!directions.current.has(id)) directions.current.set(id, directions.current.size % 2 ? 1 : -1);
      if (!offsets.current.has(id)) offsets.current.set(id, -37 * offsets.current.size);
    }
  }, [rows]);

  useEffect(() => {
    if (reduced) return;
    let frame = 0;
    let last = performance.now();
    let factor = 1;
    const step = (now: number) => {
      const dt = Math.min(now - last, 64); // a background tab must not teleport the rows
      last = now;
      factor = easeSpeed(factor, slowRef.current ? TRAILER_FACTOR : 1, dt);
      orderRef.current.forEach((id, i) => {
        const el = rowEls.current.get(id);
        if (!el) return;
        const n = el.children.length / 2;
        const second = el.children[n] as HTMLElement | undefined;
        const period = second ? second.offsetLeft : 0; // start of the duplicate set = exact loop length
        const speed = variedRef.current ? VARIED_SPEEDS[i % VARIED_SPEEDS.length] : EVEN_SPEED;
        const next = advance(offsets.current.get(id) ?? 0, (directions.current.get(id) ?? -1) * speed * factor * (dt / 1000), period);
        offsets.current.set(id, next);
        el.style.transform = `translate3d(${next}px, 0, 0)`;
      });
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [reduced]);

  return (
    <div className="tile-rows">
      {rows.map(({ world, movies }) => (
        <div key={world.id} className="tile-row-wrap" data-world={world.id}>
          <div className="tile-row-viewport">
          <div
            className="tile-row"
            data-testid="tile-row"
            ref={(el) => {
              if (el) rowEls.current.set(world.id, el);
              else rowEls.current.delete(world.id);
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

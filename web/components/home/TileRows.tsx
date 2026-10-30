"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { MoodWorld, Movie, TileRow } from "@/lib/types";

type Props = { rows: TileRow[]; variedSpeed: boolean; worldOrder?: string[] };

const EVEN_SPEED = 120; // px per second: background motion, not something to catch
const VARIED_SPEEDS = [100, 160, 85, 135];

/** Moves an offset and wraps it into (-period, 0] — exactly one loop period, so the seam never jumps. */
export function advance(offset: number, delta: number, period: number): number {
  let next = offset + delta;
  if (period > 0) {
    while (next <= -period) next += period;
    while (next > 0) next -= period;
  }
  return next;
}

/** Neighbouring worlds run in opposite directions; fixed by the world's place in the full list. */
export function rowDirection(id: string, order: string[], slot: number): number {
  const i = order.indexOf(id);
  return (i >= 0 ? i : slot) % 2 ? 1 : -1;
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

/** One row per mood world; neighbouring rows run in opposite directions in seamless loops (spec §4).
 *  Purely a background animation: blurred, see-through and not interactive. */
export default function TileRows({ rows, variedSpeed, worldOrder = [] }: Props) {
  // state per world (not per row slot): rows reorder when the hero world changes and must not jump
  const rowEls = useRef(new Map<string, HTMLDivElement>());
  const offsets = useRef(new Map<string, number>());
  const directions = useRef(new Map<string, number>());
  const reduced = useReducedMotion();
  const variedRef = useRef(variedSpeed);
  const orderRef = useRef<string[]>([]);
  useEffect(() => {
    variedRef.current = variedSpeed;
  }, [variedSpeed]);
  useEffect(() => {
    orderRef.current = rows.map((r) => r.world.id);
    orderRef.current.forEach((id, slot) => {
      if (!directions.current.has(id)) directions.current.set(id, rowDirection(id, worldOrder, slot));
      if (!offsets.current.has(id)) offsets.current.set(id, -37 * offsets.current.size);
    });
  }, [rows, worldOrder]);

  useEffect(() => {
    if (reduced) return;
    let frame = 0;
    let last = performance.now();
    const step = (now: number) => {
      const dt = Math.min(now - last, 64); // a background tab must not teleport the rows
      last = now;
      orderRef.current.forEach((id, i) => {
        const el = rowEls.current.get(id);
        if (!el) return;
        const n = el.children.length / 2;
        const first = el.children[0] as HTMLElement | undefined;
        const second = el.children[n] as HTMLElement | undefined;
        // distance from the first tile to the first tile of the duplicate set = exact loop length
        const period = first && second ? second.offsetLeft - first.offsetLeft : 0;
        const speed = variedRef.current ? VARIED_SPEEDS[i % VARIED_SPEEDS.length] : EVEN_SPEED;
        const next = advance(offsets.current.get(id) ?? 0, (directions.current.get(id) ?? -1) * speed * (dt / 1000), period);
        offsets.current.set(id, next);
        el.style.transform = `translate3d(${next}px, 0, 0)`;
      });
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [reduced]);

  return (
    <div className="tile-rows" aria-hidden="true">
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
                <div key={`${m.id}-${i}`} className="tile">
                  <TileImage movie={m} />
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { MoodWorld, Movie, TileRow } from "@/lib/types";

type Props = { rows: TileRow[]; onSelect: (m: Movie) => void; variedSpeed: boolean; worldOrder?: string[] };

const EVEN_SPEED = 40; // px per second, the pace of the genre page's related row
const VARIED_SPEEDS = [34, 52, 28];
const POINTING_FACTOR = 0.45; // pointer over the rows: slower, so a tile is easy to catch
const TRAILER_FACTOR = 0.06; // a trailer plays: the rows crawl on, the tile stays under the pointer

/** Speed factor the rows ease towards; never zero, the rows always keep moving. */
export function targetFactor(pointing: boolean, trailer: boolean): number {
  return trailer ? TRAILER_FACTOR : pointing ? POINTING_FACTOR : 1;
}
const EASE_MS = 600; // time constant for speed changes
const FEATURED_AT = 0.45; // new chat picks start here (share of the row's width), clear of the fade on the left

/** Moves an offset and wraps it into (-period, 0] — exactly one loop period, so the seam never jumps. */
export function advance(offset: number, delta: number, period: number): number {
  let next = offset + delta;
  if (period > 0) {
    while (next <= -period) next += period;
    while (next > 0) next -= period;
  }
  return next;
}

/** Offset that puts the first tile of the duplicate set at `share` of the viewport, wrapped into (-period, 0]. */
export function featuredStart(viewportWidth: number, period: number, share: number): number {
  return advance(0, viewportWidth * share - period, period);
}

/** Exponential easing towards a target (frame-rate independent); `tauMs` is the time constant. */
export function easeTowards(current: number, target: number, dtMs: number, tauMs: number): number {
  return target + (current - target) * Math.exp(-dtMs / tauMs);
}

/** Neighbouring worlds run in opposite directions; fixed by the world's place in the full list. */
export function rowDirection(id: string, order: string[], slot: number): number {
  const i = order.indexOf(id);
  return (i >= 0 ? i : slot) % 2 ? 1 : -1;
}

/** During a search the short list runs right and every row around it left; otherwise worlds alternate. */
export function searchAwareDirection(id: string, picked: boolean, searching: boolean, order: string[], slot: number): number {
  if (searching) return picked ? 1 : -1;
  return rowDirection(id, order, slot);
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

/** One row per mood world; neighbouring rows run in opposite directions in seamless loops (spec §4).
 *  No hover trailers here: the home tiles only open the film; trailers play on the genre page and under chat picks. */
export default function TileRows({ rows, onSelect, variedSpeed, worldOrder = [] }: Props) {
  // state per world (not per row slot): rows reorder when the hero world changes and must not jump
  const rowEls = useRef(new Map<string, HTMLDivElement>());
  const offsets = useRef(new Map<string, number>());
  const directions = useRef(new Map<string, number>());
  const reduced = useReducedMotion();
  const { activeId } = useActiveTrailer();
  const slowRef = useRef(false);
  const pointingRef = useRef(false);
  const variedRef = useRef(variedSpeed);
  const orderRef = useRef<string[]>([]);
  const featuredKeys = useRef(new Map<string, string>());
  const toAlign = useRef(new Set<string>()); // rows whose new chat picks must be brought into view
  useEffect(() => {
    slowRef.current = activeId !== null; // a playing trailer must not slide away from under the pointer
    variedRef.current = variedSpeed;
  }, [variedSpeed, activeId]);
  useEffect(() => {
    orderRef.current = rows.map((r) => r.world.id);
    const searching = rows.some((r) => r.picked);
    rows.forEach(({ world, picked, featured = [] }, slot) => {
      directions.current.set(world.id, searchAwareDirection(world.id, Boolean(picked), searching, worldOrder, slot));
      const key = featured.join(",");
      if (key && featuredKeys.current.get(world.id) !== key) toAlign.current.add(world.id);
      featuredKeys.current.set(world.id, key);
      if (!offsets.current.has(world.id)) offsets.current.set(world.id, -37 * offsets.current.size);
    });
  }, [rows, worldOrder]);

  useEffect(() => {
    if (reduced) return;
    let frame = 0;
    let last = performance.now();
    let factor = 1;
    const step = (now: number) => {
      const dt = Math.min(now - last, 64); // a background tab must not teleport the rows
      last = now;
      factor = easeSpeed(factor, targetFactor(pointingRef.current, slowRef.current), dt);
      orderRef.current.forEach((id, i) => {
        const el = rowEls.current.get(id);
        if (!el) return;
        const n = el.children.length / 2;
        const first = el.children[0] as HTMLElement | undefined;
        const second = el.children[n] as HTMLElement | undefined;
        // distance from the first tile to the first tile of the duplicate set = exact loop length
        const period = first && second ? second.offsetLeft - first.offsetLeft : 0;
        if (toAlign.current.has(id) && period > 0) {
          offsets.current.set(id, featuredStart(el.parentElement?.clientWidth ?? 0, period, FEATURED_AT));
          toAlign.current.delete(id);
        }
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
    <div
      className="tile-rows"
      onPointerEnter={() => {
        pointingRef.current = true;
      }}
      onPointerLeave={() => {
        pointingRef.current = false;
      }}
    >
      {rows.map(({ world, movies, picked, featured = [] }) => (
        <div key={world.id} className={`tile-row-wrap${picked ? " tile-row-wrap--picked" : ""}`} data-world={world.id}>
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
              <div key={`${m.id}-${i}`} className={`tile-wrap${featured.includes(m.id) ? " tile-wrap--featured" : ""}`}>
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
              </div>
            ))}
          </div>
          </div>
        </div>
      ))}
    </div>
  );
}

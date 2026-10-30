"use client";

import { type ReactNode, useEffect, useRef } from "react";
import { advance, easeTowards } from "@/components/home/TileRows";
import HoverTrailer from "@/components/media/HoverTrailer";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { Movie, RankedMovie } from "@/lib/types";

const IDLE_SPEED = 40; // px per second while the pointer is elsewhere: the row keeps running through
const SLOW_SPEED = 14; // px per second in the middle: still moving, but a card is easy to catch
const MAX_SPEED = 1100; // px per second with the pointer at the very edge
const DEAD_ZONE = 0.3; // middle share of the row where it only creeps on
const EASE_MS = 220;

/** Row velocity for a pointer at `ratio` (0 = left edge, 1 = right edge) of the row; null = no pointer.
 *  Right of the middle the films slide left (more come in from the right), left of it the other way,
 *  faster towards the edge. In the middle and without a pointer the row keeps going in direction `dir`. */
export function edgeSpeed(ratio: number | null, dir = -1): number {
  if (ratio === null) return dir * IDLE_SPEED;
  const d = (Math.min(Math.max(ratio, 0), 1) - 0.5) * 2; // -1 … 1
  const reach = (Math.abs(d) - DEAD_ZONE) / (1 - DEAD_ZONE);
  if (reach <= 0) return dir * SLOW_SPEED;
  return -Math.sign(d) * Math.max(reach * reach * MAX_SPEED, SLOW_SPEED);
}

/** Matching films in an endless row across the page that always runs through, steered by the mouse: towards an
 *  edge it runs fast in that direction, in the middle it creeps on. Hovering a card plays its trailer. */
export default function RelatedRow({
  items,
  onSelect,
  label = "Also fits your mood",
  name = "Also fits your mood",
  showReasons = false,
}: {
  items: RankedMovie[];
  onSelect: (m: Movie) => void;
  label?: ReactNode;
  name?: string;
  showReasons?: boolean;
}) {
  const viewport = useRef<HTMLDivElement | null>(null);
  const track = useRef<HTMLDivElement | null>(null);
  const pointer = useRef<number | null>(null);
  const trailerRef = useRef(false);
  const reduced = useReducedMotion();
  const { activeId } = useActiveTrailer();
  useEffect(() => {
    trailerRef.current = activeId !== null; // a playing trailer must not slide away from under the pointer
  }, [activeId]);

  useEffect(() => {
    if (reduced) return;
    let frame = 0;
    let last = performance.now();
    let offset = 0;
    let speed = 0;
    let dir = -1; // keep the last direction, so the row never turns around on its own
    const step = (now: number) => {
      const dt = Math.min(now - last, 64); // a background tab must not teleport the row
      last = now;
      const el = track.current;
      if (el) {
        const n = el.children.length / 2;
        const first = el.children[0] as HTMLElement | undefined;
        const second = el.children[n] as HTMLElement | undefined;
        const period = first && second ? second.offsetLeft - first.offsetLeft : 0;
        const target = edgeSpeed(pointer.current, dir);
        if (Math.abs(target) > SLOW_SPEED) dir = Math.sign(target);
        speed = easeTowards(speed, trailerRef.current ? 0 : target, dt, EASE_MS);
        offset = advance(offset, speed * (dt / 1000), period);
        el.style.transform = `translate3d(${offset}px, 0, 0)`;
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [reduced]);

  if (items.length === 0) return null;
  const onMove = (e: React.PointerEvent) => {
    const box = viewport.current?.getBoundingClientRect();
    if (box && box.width > 0) pointer.current = (e.clientX - box.left) / box.width;
  };
  return (
    <section className="related" aria-label={name}>
      <h3 className="related-label">
        {label} <span className="related-hint">· move the mouse left or right to browse</span>
      </h3>
      <div
        ref={viewport}
        className={`related-viewport ${reduced ? "is-static" : ""}`}
        onPointerMove={onMove}
        onPointerLeave={() => {
          pointer.current = null;
        }}
      >
        <div ref={track} className="related-track">
          {(reduced ? items : [...items, ...items]).map((r, i) => (
            <HoverTrailer key={`${r.movie.id}-${i}`} movie={r.movie} className="related-wrap">
              <button
                type="button"
                className="related-card"
                aria-label={`${r.movie.title}, ${r.match_percent}% match`}
                tabIndex={i < items.length ? 0 : -1}
                aria-hidden={i < items.length ? undefined : true}
                onClick={() => onSelect(r.movie)}
              >
                <ImageOrPlaceholder src={r.movie.poster_url} alt="" />
                <i>{r.match_percent}%</i>
                <span>
                  {r.movie.title}
                  {showReasons && r.reasons.length > 0 && <small className="related-why">{r.reasons[0]}</small>}
                </span>
              </button>
            </HoverTrailer>
          ))}
        </div>
      </div>
    </section>
  );
}

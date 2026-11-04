"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { advance, easeTowards } from "@/components/home/TileRows";
import { isTyping } from "@/lib/typingPause";
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
export const MIN_SLOTS = 14; // until the row is measured: fewer films than this stand still instead of looping

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

/** Keeps the card under the pointer in place when the layout shifts (a wide trailer card before it shrinks or
 *  grows): its layout position moved from `before` to `now`, so the row's offset moves the other way. */
export function anchored(offset: number, before: number | null, now: number): number {
  return before === null ? offset : offset - (now - before);
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
  const anchor = useRef<HTMLElement | null>(null); // the card under the pointer
  const trailerRef = useRef(false);
  const reduced = useReducedMotion();
  // films that all fit in the visible width stand still, left-aligned; only a row wider than the screen loops
  // (looping a short one would need empty boxes). Measured with a ResizeObserver; until then: by count.
  const [fits, setFits] = useState<boolean | null>(null);
  const still = reduced || (fits ?? items.length < MIN_SLOTS);
  useEffect(() => {
    const view = viewport.current;
    if (!view || typeof ResizeObserver === "undefined") return;
    const measure = () => {
      const el = track.current;
      const card = (el?.children[0] as HTMLElement | undefined)?.offsetWidth ?? 0;
      if (!el || !card || !view.clientWidth) return setFits(null);
      const gap = parseFloat(getComputedStyle(el).columnGap) || 0;
      setFits(items.length * card + (items.length - 1) * gap <= view.clientWidth);
    };
    const observer = new ResizeObserver(measure);
    observer.observe(view);
    return () => observer.disconnect();
  }, [items.length]);
  const { activeId } = useActiveTrailer();
  useEffect(() => {
    trailerRef.current = activeId !== null; // a playing trailer must not slide away from under the pointer
  }, [activeId]);

  useEffect(() => {
    if (still) {
      // the loop moves the track by hand: a row that shrank to a few films must start at the left again,
      // or its cards stay wherever the loop had slid them (off screen)
      if (track.current) track.current.style.transform = "";
      return;
    }
    let frame = 0;
    let last = performance.now();
    let offset = 0;
    let speed = 0;
    let dir = -1; // keep the last direction, so the row never turns around on its own
    let anchorEl: HTMLElement | null = null;
    let anchorLeft: number | null = null; // its layout position (offsetLeft ignores our transform)
    const step = (now: number) => {
      const dt = Math.min(now - last, 64); // a background tab must not teleport the row
      last = now;
      const el = track.current;
      if (isTyping()) {
        speed = 0; // hold still while the visitor types in the chat drawer; ease back up afterwards
      } else if (el) {
        const n = el.children.length / 2;
        const first = el.children[0] as HTMLElement | undefined;
        const second = el.children[n] as HTMLElement | undefined;
        const period = first && second ? second.offsetLeft - first.offsetLeft : 0;
        if (anchor.current !== anchorEl) {
          anchorEl = anchor.current;
          anchorLeft = null;
        }
        if (anchorEl) {
          offset = anchored(offset, anchorLeft, anchorEl.offsetLeft);
          anchorLeft = anchorEl.offsetLeft;
        }
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
  }, [still]);

  if (items.length === 0) return null;
  const slots = items;
  const onMove = (e: React.PointerEvent) => {
    const box = viewport.current?.getBoundingClientRect();
    if (box && box.width > 0) pointer.current = (e.clientX - box.left) / box.width;
    anchor.current = (e.target as HTMLElement).closest?.(".related-wrap") ?? null;
  };
  return (
    <section className="related" aria-label={name}>
      <h3 className="related-label">
        {label} {!still && <span className="related-hint">· move the mouse left or right to browse</span>}
      </h3>
      <div
        ref={viewport}
        className={`related-viewport ${still ? "is-static" : ""}`}
        onPointerMove={onMove}
        onPointerLeave={() => {
          pointer.current = null;
          anchor.current = null;
        }}
      >
        <div ref={track} className="related-track">
          {(still ? slots : [...slots, ...slots]).map((r, i) => (
            <HoverTrailer key={`${r.movie.id}-${i}`} movie={r.movie} className="related-wrap">
              <button
                type="button"
                className="related-card"
                aria-label={`${r.movie.title}, ${r.match_percent}% match`}
                tabIndex={i < slots.length ? 0 : -1}
                aria-hidden={i < slots.length ? undefined : true}
                onClick={() => onSelect(r.movie)}
              >
                <ImageOrPlaceholder src={r.movie.poster_url} alt="" />
                <i>{r.match_percent}%</i>
                <span>
                  {r.movie.title}
                  {showReasons && r.reasons.length > 0 && <small className="related-why">{r.reasons.slice(0, 2).join(" · ")}</small>}
                  {showReasons &&
                    r.misses?.map((m) => (
                      <small key={m} className="result-miss">
                        ≠ {m}
                      </small>
                    ))}
                </span>
              </button>
            </HoverTrailer>
          ))}
        </div>
      </div>
    </section>
  );
}

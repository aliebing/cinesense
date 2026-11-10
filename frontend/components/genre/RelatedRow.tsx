"use client";

import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { advance, easeTowards } from "@/components/home/TileRows";
import { isTyping } from "@/lib/typingPause";
import HoverTrailer from "@/components/media/HoverTrailer";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { useActiveTrailer } from "@/lib/useActiveTrailer";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { Movie, RankedMovie } from "@/lib/types";

const IDLE_SPEED = 40; // px per second while the pointer is elsewhere: the row keeps running through
const SLOW_SPEED = 14; // px per second in the middle: still moving, but a card is easy to catch
const MAX_SPEED = 650; // px per second with the pointer at the very edge
const DEAD_ZONE = 0.3; // middle share of the row where it only creeps on
const EASE_MS = 650; // smooth: the row picks up speed gently and slows down gently
export const SWEEP_MS = 1500; // the run to the next (or previous) page of results
const SWEEP_LAPS = 1; // extra laps round the endless row on the way: a long, very fast run
export const MIN_SLOTS = 14; // until the row is measured: fewer films than this stand still instead of looping
const SLIDE_CARDS = 4; // how far one « » click slides the row
const LOOP_MIN = 4; // a forced loop (results page) needs at least this many films, fewer stand still

/** Row velocity for a pointer at `ratio` (0 = left edge, 1 = right edge) of the row; null = no pointer.
 *  Right of the middle the films slide left (more come in from the right), left of it the other way,
 *  faster towards the edge. In the middle and without a pointer the row keeps going in direction `dir`, unless
 *  `drift` is off (search results: the best matches stay in front until the mouse browses). */
export function edgeSpeed(ratio: number | null, dir = -1, drift = true): number {
  if (ratio === null) return drift ? dir * IDLE_SPEED : 0;
  const d = (Math.min(Math.max(ratio, 0), 1) - 0.5) * 2; // -1 … 1
  const reach = (Math.abs(d) - DEAD_ZONE) / (1 - DEAD_ZONE);
  if (reach <= 0) return drift ? dir * SLOW_SPEED : 0;
  return -Math.sign(d) * Math.max(reach * reach * MAX_SPEED, SLOW_SPEED);
}

const MOVING_SPEED = 30; // px per second above which a row counts as moving: hover trailers wait until it rests
/** Velocity for a row with a start and an end (offset 0 … `min`, negative): the steered `target` until the row
 *  reaches the end it runs to, then nothing: it stops at once with its first or last film in full view. */
export function braked(target: number, offset: number, min: number): number {
  const room = target < 0 ? offset - min : -offset; // px left before that end
  return room <= 0 ? 0 : target;
}

/** Keeps the card under the pointer in place when the layout shifts (a wide trailer card before it shrinks or
 *  grows): its layout position moved from `before` to `now`, so the row's offset moves the other way. */
export function anchored(offset: number, before: number | null, now: number): number {
  return before === null ? offset : offset - (now - before);
}

/** Row offset during a sweep: from `start` to `target` in `ms`, slow at both ends and very fast in between. */
export function sweepOffset(start: number, target: number, elapsed: number, ms = SWEEP_MS): number {
  const t = Math.min(Math.max(elapsed / ms, 0), 1);
  const eased = t < 0.5 ? 16 * t ** 5 : 1 - (-2 * t + 2) ** 5 / 2; // ease-in-out (quintic): gentle ends, a rush between
  return start + (target - start) * eased;
}

/** A run through the row to another page: the row holds both pages, the cards from index `from` on are where the
 *  old row's first card was, and it ends with card `to` where the first card stands at rest (then the caller swaps
 *  in the new page alone, at rest — the same picture). */
export type Sweep = { from: number; to: number; onDone: () => void };

export function LoadingBar() {
  return <div className="loading-bar" role="progressbar" aria-label="Loading results" />;
}

/** Matching films in an endless row across the page that always runs through, steered by the mouse: towards an
 *  edge it runs fast in that direction, in the middle it creeps on. Hovering a card plays its trailer. */
export default function RelatedRow({
  items,
  onSelect,
  label = "Also fits your mood",
  name = "Also fits your mood",
  showReasons = false,
  busy = false,
  drift = false,
  after,
  sweep = null,
  found = null,
  streamCheck = false,
  bar = true,
  loop = false,
  arrows = false,
  paging = null,
  bounded = false,
}: {
  items: RankedMovie[];
  onSelect: (m: Movie) => void;
  label?: ReactNode;
  name?: string;
  /** how many films the search found, as a readable line above the label ("65 films found"); null: no line */
  found?: { total: number; capped?: boolean } | null;
  /** the streaming filter is on: cards whose streaming was not looked up yet say so */
  streamCheck?: boolean;
  showReasons?: boolean;
  /** new results are loading: a running bar above the cards, the old cards dimmed */
  busy?: boolean;
  /** false: no loading bar of its own while busy (the page already shows one) */
  bar?: boolean;
  /** run as an endless row even when the films would fit (from LOOP_MIN films on; repeated to fill the width) */
  loop?: boolean;
  /** « » buttons on both sides that slide the row by most of its width */
  arrows?: boolean;
  /** a row with a start and an end instead of an endless loop: the mouse browses it, and it comes to rest at its
   *  first and last film */
  bounded?: boolean;
  /** with « »: they page instead of sliding (a null handler: no page that way) */
  paging?: { size: number; prev: (() => void) | null; next: (() => void) | null } | null;
  /** true: the row keeps running on its own; false (default): it moves only while the mouse steers towards an edge */
  drift?: boolean;
  /** placed after the cards, inside the row (the results page's "load more" arrow) */
  after?: ReactNode;
  /** run quickly through the row to card `sweep.to` (paging the results), then call `onDone` */
  sweep?: Sweep | null;
}) {
  const viewport = useRef<HTMLDivElement | null>(null);
  const track = useRef<HTMLDivElement | null>(null);
  const pointer = useRef<number | null>(null);
  const anchor = useRef<HTMLElement | null>(null); // the card under the pointer
  const trailerRef = useRef(false);
  const nudge = useRef(0); // px the « » buttons still want the running row to slide (eased off over a few frames)
  const reduced = useReducedMotion();
  const sweepRef = useRef<Sweep | null>(sweep);
  useLayoutEffect(() => {
    sweepRef.current = sweep; // before the next frame: the row already holds both pages
  }, [sweep]);
  // films that all fit in the visible width stand still, left-aligned; only a row wider than the screen loops
  // (looping a short one would need empty boxes). Measured with a ResizeObserver; until then: by count.
  const [fits, setFits] = useState<boolean | null>(null);
  const looping = loop && !bounded && items.length >= LOOP_MIN;
  const still = reduced || (!looping && (fits ?? items.length < MIN_SLOTS));
  useEffect(() => {
    const view = viewport.current;
    if (!view || typeof ResizeObserver === "undefined") return;
    const measure = () => {
      const el = track.current;
      // the narrowest card is the normal width; a card widened by its trailer must not count (it made a
      // fitting row flip into the loop and back while the trailer played)
      const widths = el ? [...el.children].map((c) => (c as HTMLElement).offsetWidth).filter((w) => w > 0) : [];
      const card = widths.length ? Math.min(...widths) : 0;
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

  const sweeping = sweep !== null;
  useEffect(() => {
    if (sweeping && still) sweepRef.current?.onDone(); // nothing to run through: swap the page at once
  }, [sweeping, still]);

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
    // the caller builds a new Sweep object on every render: one run per from/to, until the row is swapped
    let run: { from: number; to: number; start: number; target: number; end: number; lap: number; began: number; done: boolean } | null =
      null;
    const step = (now: number) => {
      const dt = Math.min(now - last, 64); // a background tab must not teleport the row
      last = now;
      const el = track.current;
      const sweepNow = sweepRef.current;
      if (el && sweepNow) {
        if (!run || run.from !== sweepNow.from || run.to !== sweepNow.to) {
          const left = (i: number) => {
            const card = el.children[Math.min(i, el.children.length - 1)] as HTMLElement | undefined;
            const first = el.children[0] as HTMLElement | undefined;
            return card && first ? card.offsetLeft - first.offsetLeft : 0;
          };
          // the old row's cards now start at `from`: shift so they stay where they were, then run to `to`,
          // the long way round: SWEEP_LAPS more laps of the endless row in the same direction
          const start = offset - left(sweepNow.from);
          const half = el.children.length / 2;
          const lap = !bounded && half >= 1 ? left(half) : 0; // a row with ends has no laps to run
          const end = -left(sweepNow.to);
          const target = end + (end < start ? -1 : 1) * SWEEP_LAPS * lap;
          run = { from: sweepNow.from, to: sweepNow.to, start, target: lap > 0 ? target : end, end, lap, began: now, done: false };
        }
        const elapsed = run.start === run.target ? SWEEP_MS : now - run.began;
        const raw = sweepOffset(run.start, run.target, elapsed);
        // the cards repeat every lap: show the run within one lap, and end exactly where the new page starts
        offset = elapsed >= SWEEP_MS ? run.end : run.lap > 0 ? ((raw % run.lap) - run.lap) % run.lap : raw;
        speed = 0;
        el.style.transform = `translate3d(${offset}px, 0, 0)`;
        if (elapsed >= SWEEP_MS && !run.done) {
          run.done = true;
          sweepNow.onDone();
        }
      } else if (run) {
        run = null; // a cancelled sweep (a new search): carry on from where it stopped
      } else if (isTyping()) {
        speed = 0; // hold still while the visitor types in the chat drawer; ease back up afterwards
      } else if (el && bounded) {
        const view = viewport.current;
        const min = Math.min(0, (view?.clientWidth ?? 0) - el.offsetWidth);
        if (anchor.current !== anchorEl) {
          anchorEl = anchor.current;
          anchorLeft = null;
        }
        if (anchorEl) {
          offset = anchored(offset, anchorLeft, anchorEl.offsetLeft);
          anchorLeft = anchorEl.offsetLeft;
        }
        if (nudge.current !== 0) {
          const part = Math.abs(nudge.current) < 1 ? nudge.current : nudge.current * Math.min(1, dt / 160);
          nudge.current -= part;
          offset += part;
        }
        // steering towards an edge always browses (the trailer under the pointer stops when its card slides away);
        // in the calm middle the row stands still anyway, so a trailer there plays in place
        const target = braked(edgeSpeed(pointer.current, dir, false), offset, min);
        speed = easeTowards(speed, target, dt, EASE_MS);
        const next = offset + speed * (dt / 1000);
        if (next <= min || next >= 0) speed = 0; // an end: stop dead there, no easing out
        offset = Math.min(0, Math.max(min, next));
        el.style.transform = `translate3d(${offset}px, 0, 0)`;
        // no fade on the side where the row ends: its first and last film show in full
        view?.classList.toggle("is-start", offset >= -0.5);
        view?.classList.toggle("is-end", offset <= min + 0.5);
        view?.classList.toggle("is-moving", Math.abs(speed) > MOVING_SPEED); // no trailer starts while it moves
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
        if (nudge.current !== 0) {
          const part = Math.abs(nudge.current) < 1 ? nudge.current : nudge.current * Math.min(1, dt / 160);
          nudge.current -= part;
          offset = advance(offset, part, period);
        }
        const target = edgeSpeed(pointer.current, dir, drift);
        if (Math.abs(target) > SLOW_SPEED) dir = Math.sign(target);
        speed = easeTowards(speed, trailerRef.current ? 0 : target, dt, EASE_MS);
        offset = advance(offset, speed * (dt / 1000), period);
        el.style.transform = `translate3d(${offset}px, 0, 0)`;
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [still, drift, bounded]);

  if (items.length === 0) return null;
  // a forced loop repeats short rows until they are wider than the screen, so the run has no gap at its seam
  const slots = looping && !still && items.length < MIN_SLOTS ? Array.from({ length: Math.ceil(MIN_SLOTS / items.length) }, () => items).flat() : items;
  const slide = (dir: 1 | -1) => {
    // SLIDE_CARDS cards at a time: a run of the whole width could be exactly one loop and look like no move at all
    const el = track.current;
    const a = el?.children[0] as HTMLElement | undefined;
    const b = el?.children[1] as HTMLElement | undefined;
    const step = a && b ? b.offsetLeft - a.offsetLeft : 0;
    const width = step > 0 ? step * SLIDE_CARDS : (viewport.current?.clientWidth ?? 0) * 0.5;
    if (still) viewport.current?.scrollBy?.({ left: dir * width, behavior: reduced ? "auto" : "smooth" });
    else nudge.current -= dir * width; // the loop moves the track: a negative offset shows later films
  };
  const onMove = (e: React.PointerEvent) => {
    const box = viewport.current?.getBoundingClientRect();
    if (box && box.width > 0) pointer.current = (e.clientX - box.left) / box.width;
    anchor.current = (e.target as HTMLElement).closest?.(".related-wrap") ?? null;
  };
  return (
    <section className={`related ${busy ? "is-busy" : ""} ${sweeping ? "is-sweeping" : ""} ${arrows ? "has-arrows" : ""} ${bounded ? "has-ends" : ""}`} aria-label={name} aria-busy={busy}>
      {found && <p className="related-count">{foundText(found.total, found.capped)}</p>}
      <h3 className="related-label">
        {label} {!still && <span className="related-hint">· move the mouse left or right to browse</span>}
      </h3>
      {busy && bar && <LoadingBar />}
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
          {(still || bounded ? slots : [...slots, ...slots]).map((r, i) => (
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
                <i title={MATCH_HINT}>{r.match_percent}% match</i>
                <span>
                  {r.movie.title}
                  {showReasons && r.reasons.length > 0 && <small className="related-why">{r.reasons.slice(0, 2).join(" · ")}</small>}
                  {streamCheck && r.movie.availability.streaming_de === null && (
                    <small className="result-unchecked">? streaming not checked</small>
                  )}
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
      {/* « » only where there is somewhere to go: paging shows each arrow only with a page that way, sliding only
          when the films do not all fit */}
      {arrows && (paging ? paging.prev : !still) && (
        <button
          type="button"
          className="row-arrow row-arrow--left"
          aria-label={paging ? `Previous ${paging.size}` : "Slide left"}
          title={paging ? `Previous ${paging.size}` : "Slide left"}
          disabled={sweeping}
          onClick={() => (paging ? paging.prev?.() : slide(-1))}
        >
          «
        </button>
      )}
      {arrows && (paging ? paging.next : !still) && (
        <button
          type="button"
          className="row-arrow row-arrow--right"
          aria-label={paging ? `Next ${paging.size}` : "Slide right"}
          title={paging ? `Next ${paging.size}` : "Slide right"}
          disabled={sweeping}
          onClick={() => (paging ? paging.next?.() : slide(1))}
        >
          »
        </button>
      )}
      {after}
    </section>
  );
}

const fmt = new Intl.NumberFormat("en-US");

/** "65 films found", "1 film found", "At least 500 films found" (a capped mood search) */
/** what the percentage on a card means: fit to this search, not a review score (that is the MovieLens rating) */
export const MATCH_HINT = "How well the film fits your search (moods, plot, people, rating), not a review score";

export function foundText(total: number, capped = false): string {
  const films = `${fmt.format(total)} ${total === 1 ? "film" : "films"} found`;
  return capped ? `At least ${films}` : films;
}

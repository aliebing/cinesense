"use client";

import { useRouter } from "next/navigation";
import { type CSSProperties, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import HoverTrailer from "@/components/media/HoverTrailer";
import ImageOrPlaceholder from "@/components/ui/ImageOrPlaceholder";
import { useChatLog, useChatStatus } from "@/lib/chat";
import type { RankedMovie } from "@/lib/types";
import { useIsNarrow, useReducedMotion } from "@/lib/useReducedMotion";

const MAX_CARDS = 8;
const DEAL_MS = 650; // one card's flight from the deck to its place
const DEAL_STAGGER_MS = 140; // next card leaves the deck this much later
const GATHER_MS = 320;
const GATHER_STAGGER_MS = 40;
const EASE = "cubic-bezier(.2,.8,.2,1)";

/** Offset from a card's place to the deck centre, with a little tilt so the pile looks hand-stacked. */
function toDeck(card: HTMLElement, deck: HTMLElement, i: number) {
  const c = card.getBoundingClientRect();
  const d = deck.getBoundingClientRect();
  const dx = d.left + d.width / 2 - (c.left + c.width / 2);
  const dy = d.top + d.height / 2 - (c.top + c.height / 2);
  return `translate(${dx}px, ${dy}px) rotate(${((i * 37) % 11) - 5}deg) scale(.92)`;
}

function cardsOf(grid: HTMLElement | null): HTMLElement[] {
  return grid ? [...grid.querySelectorAll<HTMLElement>(".deal-card")] : [];
}

/** Each card flies from the deck to its place, turning face up on the way (no-op where WAAPI is missing). */
function deal(grid: HTMLElement | null, deck: HTMLElement | null) {
  if (!deck) return;
  cardsOf(grid).forEach((card, i) => {
    if (typeof card.animate !== "function") return;
    const timing = { duration: DEAL_MS, delay: i * DEAL_STAGGER_MS, easing: EASE, fill: "backwards" as const };
    card.animate([{ transform: toDeck(card, deck, i) }, { transform: "none" }], timing);
    card
      .querySelector<HTMLElement>(".deal-card__inner")
      ?.animate([{ transform: "rotateY(180deg)" }, { transform: "rotateY(180deg)", offset: 0.3 }, { transform: "none" }], timing);
  });
}

/** The reverse: every card turns face down and flies back onto the deck; resolves when the last one lands. */
function gather(grid: HTMLElement | null, deck: HTMLElement | null): Promise<unknown> {
  const cards = cardsOf(grid);
  if (!deck || cards.length === 0 || typeof cards[0].animate !== "function") return Promise.resolve();
  const runs = cards.flatMap((card, i) => {
    const timing = { duration: GATHER_MS, delay: (cards.length - 1 - i) * GATHER_STAGGER_MS, easing: "ease-in", fill: "forwards" as const };
    const inner = card.querySelector<HTMLElement>(".deal-card__inner");
    return [
      card.animate([{ transform: "none" }, { transform: toDeck(card, deck, i) }], timing),
      ...(inner ? [inner.animate([{ transform: "none" }, { transform: "rotateY(180deg)" }], timing)] : []),
    ];
  });
  return Promise.all(runs.map((a) => a.finished)).catch(() => undefined);
}

/** The agent's films on the homepage, dealt like cards from a deck into the space beside the chat. While the agent
 *  works the cards go back onto the deck, which shuffles; the new answer is dealt from there. */
export default function DealtCards() {
  const router = useRouter();
  const [entries] = useChatLog();
  const busy = useChatStatus() !== null;
  const reduced = useReducedMotion();
  const narrow = useIsNarrow();
  const motion = !reduced && !narrow;

  // The newest answer that brought films; a clarifying question keeps the cards on the table.
  const latest = useMemo(() => {
    for (let i = entries.length - 1; i >= 0; i--) {
      const e = entries[i];
      if (e.role === "bot" && e.results && e.results.length > 0) return e.results;
    }
    return null;
  }, [entries]);

  const [shown, setShown] = useState<RankedMovie[] | null>(latest);
  const [onDeck, setOnDeck] = useState(false); // cards gathered, waiting for the next answer
  const deck = useRef<HTMLDivElement>(null);
  const grid = useRef<HTMLDivElement>(null);
  const gathering = useRef<Promise<unknown> | null>(null);

  const collect = () => (gathering.current ??= gather(grid.current, deck.current).finally(() => (gathering.current = null)));

  // A question was sent: put the cards back on the deck.
  useEffect(() => {
    if (!busy || !motion || !shown || onDeck) return;
    let live = true;
    void collect().then(() => live && setOnDeck(true));
    return () => {
      live = false;
    };
  }, [busy, motion, shown, onDeck]);

  // An answer arrived (or the agent gave up): deal the new films, or the old ones again. Cards still on the table
  // are gathered first; either way the swap lands after the current render.
  useEffect(() => {
    if (busy && latest === shown) return;
    if (latest === shown && !onDeck) return;
    let live = true;
    const swap = () => {
      if (!live) return;
      setShown(latest);
      setOnDeck(false);
    };
    const onTable = motion && shown && !onDeck && latest !== shown;
    void (onTable ? collect() : Promise.resolve()).then(swap);
    return () => {
      live = false;
    };
  }, [latest, busy, onDeck]); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    if (motion && shown && !onDeck) deal(grid.current, deck.current);
  }, [shown, onDeck, motion]);

  if (!shown && !busy) return null;
  const cards = (shown ?? []).slice(0, MAX_CARDS);
  const showDeck = busy || onDeck || !shown;
  const open = (r: RankedMovie) => router.push(`/world/${r.movie.world_ids[0] ?? "suspense"}?film=${r.movie.id}`);

  return (
    <section className="deal" aria-label="Films for you">
      <div ref={deck} className={`deal-deck${showDeck ? " is-on" : ""}${busy ? " is-shuffling" : ""}`} aria-hidden="true">
        {showDeck && (
          <>
            <span className="deal-back" />
            <span className="deal-back" />
            <span className="deal-back" />
            <span className="deal-deck__hit" data-testid="deal-deck" />
          </>
        )}
      </div>
      {shown && !onDeck && (
        <div ref={grid} className="deal-grid" style={{ "--cols": Math.min(4, cards.length) } as CSSProperties}>
          {cards.map((r) => (
            <article key={r.movie.id} className="deal-card" data-testid="dealt-card">
              <div className="deal-card__inner">
                <div className="deal-card__front">
                  <HoverTrailer movie={r.movie} className="deal-card__media">
                    <button type="button" aria-label={`Open ${r.movie.title}`} onClick={() => open(r)}>
                      <ImageOrPlaceholder src={r.movie.poster_url ?? r.movie.horizontal_poster_url} alt="" />
                    </button>
                  </HoverTrailer>
                  <i className="deal-card__match">{r.match_percent}%</i>
                  <div className="deal-card__text">
                    <strong>
                      {r.movie.title}
                      {r.movie.year ? ` (${r.movie.year})` : ""}
                    </strong>
                    {r.reasons[0] && <span>{r.reasons[0]}</span>}
                  </div>
                </div>
                <div className="deal-back deal-card__back" aria-hidden="true" />
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

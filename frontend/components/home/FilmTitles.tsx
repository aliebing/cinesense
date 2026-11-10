"use client";

import { useEffect, useRef, useState } from "react";
import { isTyping } from "@/lib/typingPause";
import { useReducedMotion } from "@/lib/useReducedMotion";

const INTERVAL_MS = 3700;
const LIFETIME_MS = 6800;

type Shown = { key: number; text: string; slot: "upper" | "lower" };

/** Film titles emerge from blur, stay readable, dissolve; consecutive titles alternate slots (spec §4). */
export default function FilmTitles({ titles }: { titles: string[] }) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState<Shown[]>([]);
  const counter = useRef(0);

  // the titles change with the mood on screen: the running clock keeps going and the next title comes from the new
  // list (from its start), while the ones already up fade out as usual
  const titlesRef = useRef(titles);
  useEffect(() => {
    titlesRef.current = titles;
    counter.current = 0;
  }, [titles]);
  const hasTitles = titles.length > 0;

  useEffect(() => {
    if (reduced || !hasTitles) return;
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    let slot = 0;
    const spawn = () => {
      if (isTyping()) return; // no new title while the visitor types in the chat
      const list = titlesRef.current;
      if (list.length === 0) return;
      const n = counter.current++;
      const item: Shown = { key: slot, text: list[n % list.length], slot: slot % 2 === 0 ? "upper" : "lower" };
      slot++;
      setShown((prev) => [...prev, item]);
      timeouts.push(setTimeout(() => setShown((prev) => prev.filter((s) => s.key !== item.key)), LIFETIME_MS));
    };
    spawn();
    const id = setInterval(spawn, INTERVAL_MS);
    return () => {
      clearInterval(id);
      timeouts.forEach(clearTimeout);
      setShown([]);
    };
  }, [reduced, hasTitles]);

  if (titles.length === 0) return null;
  if (reduced) {
    return (
      <div className="film-titles" data-testid="film-titles" aria-hidden="true">
        <div className="film-title is-static" data-testid="film-title" data-slot="upper">
          {titles[0]}
        </div>
      </div>
    );
  }
  return (
    <div className="film-titles" data-testid="film-titles" aria-hidden="true">
      {shown.map((s) => (
        <div key={s.key} className="film-title" data-testid="film-title" data-slot={s.slot}>
          {s.text}
        </div>
      ))}
    </div>
  );
}

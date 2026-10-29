"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "@/lib/useReducedMotion";

const INTERVAL_MS = 3700;
const LIFETIME_MS = 6800;

type Shown = { key: number; text: string; slot: "upper" | "lower" };

/** Film titles emerge from blur, stay readable, dissolve; consecutive titles alternate slots (spec §4). */
export default function FilmTitles({ titles }: { titles: string[] }) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState<Shown[]>([]);
  const counter = useRef(0);

  useEffect(() => {
    if (reduced || titles.length === 0) return;
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    const spawn = () => {
      const n = counter.current++;
      const item: Shown = { key: n, text: titles[n % titles.length], slot: n % 2 === 0 ? "upper" : "lower" };
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
  }, [reduced, titles]);

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

"use client";

import { useEffect } from "react";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { MoodWorld } from "@/lib/types";

type Props = {
  worlds: MoodWorld[];
  images: Record<string, string | null>;
  activeIndex: number;
  onAdvance: () => void;
};

const ADVANCE_MS = 7000;

/** Full-stage mood world backgrounds with slow Ken Burns motion and cross-fades. */
export default function HeroSlides({ worlds, images, activeIndex, onAdvance }: Props) {
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced || worlds.length < 2) return;
    const id = setInterval(onAdvance, ADVANCE_MS);
    return () => clearInterval(id);
  }, [reduced, worlds.length, onAdvance]);

  return (
    <div className="hero" aria-hidden="true">
      {worlds.map((w, i) => (
        <div key={w.id} className={`hero-slide${i === activeIndex ? " is-on" : ""}`}>
          <div className="hero-img" style={images[w.id] ? { backgroundImage: `url(${images[w.id]})` } : undefined} />
          <div className="hero-grade" style={{ background: w.tint }} />
        </div>
      ))}
    </div>
  );
}

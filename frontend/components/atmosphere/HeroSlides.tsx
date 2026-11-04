"use client";

import { useEffect } from "react";
import { isTyping } from "@/lib/typingPause";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { MoodWorld } from "@/lib/types";

type Props = {
  worlds: MoodWorld[];
  images: Record<string, string | null>;
  activeIndex: number;
  onAdvance: () => void;
  paused?: boolean;
};

const ADVANCE_MS = 12000; // calm: the tile rows follow each change

/** Full-stage mood world backgrounds with slow Ken Burns motion and cross-fades. */
export default function HeroSlides({ worlds, images, activeIndex, onAdvance, paused = false }: Props) {
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced || paused || worlds.length < 2) return;
    const id = setInterval(() => {
      if (!isTyping()) onAdvance(); // no cross-fade while the visitor types in the chat
    }, ADVANCE_MS);
    return () => clearInterval(id);
  }, [reduced, paused, worlds.length, onAdvance]);

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

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
  /** false: no timer of its own, the page advances (the homepage after its rows ran through all their films) */
  auto?: boolean;
};

const ADVANCE_MS = 12000; // calm: the tile rows follow each change

/** Full-stage mood world backgrounds with slow Ken Burns motion and cross-fades. */
export default function HeroSlides({ worlds, images, activeIndex, onAdvance, paused = false, auto = true }: Props) {
  const reduced = useReducedMotion();

  useEffect(() => {
    if (!auto || reduced || paused || worlds.length < 2) return;
    const id = setInterval(() => {
      if (!isTyping()) onAdvance(); // no cross-fade while the visitor types in the chat
    }, ADVANCE_MS);
    return () => clearInterval(id);
  }, [auto, reduced, paused, worlds.length, onAdvance]);

  const n = worlds.length;
  // only the slide on show, the one fading out and the next one load their picture (~80 KB each); the next one
  // has ADVANCE_MS to arrive
  const near = (i: number) => i === activeIndex || i === (activeIndex + 1) % n || i === (activeIndex - 1 + n) % n;
  return (
    <div className="hero" aria-hidden="true">
      {worlds.map((w, i) => (
        <div key={w.id} className={`hero-slide${i === activeIndex ? " is-on" : ""}`}>
          <div className="hero-img" style={images[w.id] && near(i) ? { backgroundImage: `url(${images[w.id]})` } : undefined} />
          <div className="hero-grade" style={{ background: w.tint }} />
        </div>
      ))}
    </div>
  );
}

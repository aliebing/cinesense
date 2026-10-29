"use client";

import { useReducedMotion } from "@/lib/useReducedMotion";

/**
 * Layered fog and projector light (spec §3a): three fog depths drifting at different speeds,
 * a flickering back-light, a beam passing through the haze, lens flares and a soft downward fade.
 */
export default function FogLight({ tint, reduced = false }: { tint: string; reduced?: boolean }) {
  const prefersReduced = useReducedMotion();
  const calm = reduced || prefersReduced;
  return (
    <div className="fog-light" style={{ ["--tint" as string]: tint }} data-testid="fog-light" aria-hidden="true">
      <div className="fog fog--far">
        <i />
        <i />
        <i />
      </div>
      <div className="backlight" />
      <div className="beam" />
      <div className="fog fog--mid">
        <i />
        <i />
      </div>
      {!calm && (
        <div className="fog fog--near">
          <i />
          <i />
        </div>
      )}
      <div className="flare flare--1" />
      <div className="flare flare--2" />
      <div className="flare flare--3" />
      <div className="streak" />
    </div>
  );
}

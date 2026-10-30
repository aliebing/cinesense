"use client";

import { useReducedMotion } from "@/lib/useReducedMotion";

/**
 * Layered fog and light (spec §3a): three fog depths drifting at different speeds and two soft spotlights
 * shining down from the top corners, their cones swaying slowly through the haze and fading downward.
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
      <div className="spot spot--left" />
      <div className="spot spot--right" />
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
    </div>
  );
}

/** Finger swiping for the JS-driven rows (they move by transform, so the browser cannot scroll them itself).
 *  Only touch and pen count: the mouse keeps steering the rows as before. A sideways swipe drags the row; an upright
 *  one is left to the browser (the element needs `touch-action: pan-y`), so the page still scrolls. A tap stays a
 *  click; the click that ends a drag is swallowed, so a swipe never opens a film. */

const SLOP_PX = 8; // a finger moves a little on every tap: below this it is still a tap
const CLICK_GUARD_MS = 400; // a click this soon after a drag belongs to the drag

export type TouchDrag = {
  /** the drag starts on `target` (to find the row it belongs to) */
  onStart?: (target: Element) => void;
  /** px the finger moved since the last call (positive: to the right) */
  onDrag: (dx: number) => void;
  /** the finger left the screen; `velocity` in px per second (positive: to the right) */
  onEnd?: (velocity: number) => void;
};

export function attachTouchDrag(el: HTMLElement, handlers: TouchDrag): () => void {
  let id: number | null = null;
  let startX = 0;
  let startY = 0;
  let lastX = 0;
  let lastT = 0;
  let velocity = 0;
  let dragging = false;
  let target: Element | null = null;
  let endedAt = -Infinity;

  const down = (e: PointerEvent) => {
    if (e.pointerType === "mouse" || id !== null) return;
    id = e.pointerId;
    startX = lastX = e.clientX;
    startY = e.clientY;
    lastT = e.timeStamp;
    velocity = 0;
    dragging = false;
    target = e.target instanceof Element ? e.target : null;
  };
  const move = (e: PointerEvent) => {
    if (e.pointerId !== id) return;
    if (!dragging) {
      const dx = e.clientX - startX;
      if (Math.abs(dx) < SLOP_PX || Math.abs(dx) < Math.abs(e.clientY - startY)) return;
      dragging = true;
      handlers.onStart?.(target ?? el);
      try {
        el.setPointerCapture?.(e.pointerId);
      } catch {
        // the pointer may already be gone: the drag still works without capture
      }
    }
    const dx = e.clientX - lastX;
    const dt = e.timeStamp - lastT;
    if (dt > 0) velocity = 0.7 * ((dx / dt) * 1000) + 0.3 * velocity; // smoothed: one jittery event must not fling
    lastX = e.clientX;
    lastT = e.timeStamp;
    if (dx !== 0) handlers.onDrag(dx);
  };
  const up = (e: PointerEvent) => {
    if (e.pointerId !== id) return;
    id = null;
    if (!dragging) return;
    dragging = false;
    endedAt = e.timeStamp;
    // a finger that rested before lifting does not fling
    handlers.onEnd?.(e.type === "pointercancel" || e.timeStamp - lastT > 100 ? 0 : velocity);
  };
  const click = (e: MouseEvent) => {
    if (e.timeStamp - endedAt > CLICK_GUARD_MS) return;
    e.preventDefault();
    e.stopPropagation();
  };

  el.addEventListener("pointerdown", down);
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", up);
  el.addEventListener("pointercancel", up);
  el.addEventListener("click", click, true);
  return () => {
    el.removeEventListener("pointerdown", down);
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", up);
    el.removeEventListener("pointercancel", up);
    el.removeEventListener("click", click, true);
  };
}

/** How far a row glides on after a flick, in px, for `velocity` in px per second. */
export function glideDistance(velocity: number): number {
  return velocity * 0.3;
}

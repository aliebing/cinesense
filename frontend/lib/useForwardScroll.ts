import { type RefObject, useEffect } from "react";

const LINE_PX = 40; // a wheel tick in lines (Firefox) becomes pixels
const KEYS: Record<string, (h: number) => number> = {
  PageDown: (h) => h * 0.9,
  PageUp: (h) => -h * 0.9,
  " ": (h) => h * 0.9,
  ArrowDown: () => LINE_PX,
  ArrowUp: () => -LINE_PX,
  End: () => Number.MAX_SAFE_INTEGER,
  Home: () => -Number.MAX_SAFE_INTEGER,
};

/** The page scrolls only inside the screen: a wheel over the curtains, the letterbox bars or the room around it, and
 *  the scroll keys while nothing has focus, scroll the screen's content instead of doing nothing. */
export function useForwardScroll(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      const el = ref.current;
      if (!el || e.ctrlKey || (e.target instanceof Node && el.contains(e.target))) return;
      el.scrollBy({ top: e.deltaMode === 1 ? e.deltaY * LINE_PX : e.deltaY });
    };
    const onKey = (e: KeyboardEvent) => {
      const el = ref.current;
      const by = KEYS[e.key];
      const idle = !document.activeElement || document.activeElement === document.body;
      if (!el || !by || !idle || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      el.scrollBy({ top: (e.shiftKey && e.key === " " ? -1 : 1) * by(el.clientHeight) });
    };
    window.addEventListener("wheel", onWheel, { passive: true });
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKey);
    };
  }, [ref]);
}

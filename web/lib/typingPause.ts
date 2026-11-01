// While the visitor types in the chat, the page holds all its motion (tile rows, fog, light, Ken Burns, film titles):
// any moving pixel makes the browser redraw the stage, and on a busy stage every keystroke then appeared ~0.1 s late.
// Marked on <html data-typing> so CSS can pause animations; the tile rows ask isTyping() each frame.

const RESUME_MS = 4000; // long enough that a pause to think does not restart the stage (each restart costs the next keystroke)
let timer: ReturnType<typeof setTimeout> | null = null;

function mark(on: boolean) {
  if (typeof document !== "undefined") document.documentElement.toggleAttribute("data-typing", on);
}

export function isTyping(): boolean {
  return timer !== null;
}

/** Focus or a keystroke: pause now, resume 4 s after the last one. */
export function noteTyping() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(stopTyping, RESUME_MS);
  mark(true);
}

/** Resume at once (the field lost focus, or the message was sent). */
export function stopTyping() {
  if (timer) clearTimeout(timer);
  timer = null;
  mark(false);
}

const KEY = "cinesense.user";
let memoryId: string | null = null;

/** UUID v4; crypto.randomUUID only exists in secure contexts (https, localhost). */
export function randomId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** Anonymous visitor id kept in this browser (no login, no personal data), or "" while there is none.
 * Reading never creates one: the id only exists once the visitor rates a film (ensureUserId). */
export function userId(): string {
  if (typeof window === "undefined") return ""; // never share one id between server-rendered visitors
  try {
    return window.localStorage.getItem(KEY) ?? "";
  } catch {
    return memoryId ?? "";
  }
}

/** The visitor id, created on the first 👍/👎: a random UUID (no login, no personal data). */
export function ensureUserId(): string {
  if (typeof window === "undefined") return "";
  const existing = userId();
  if (existing) return existing;
  const id = randomId();
  try {
    window.localStorage.setItem(KEY, id);
  } catch {
    memoryId = id;
  }
  return id;
}

/** Request headers carrying the visitor id; none at all while the visitor has not rated anything. */
export function userHeaders(): Record<string, string> {
  const id = userId();
  return id ? { [USER_HEADER]: id } : {};
}

export const USER_HEADER = "X-CineSense-User";

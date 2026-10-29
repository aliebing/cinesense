const KEY = "cinesense.user";
let memoryId: string | null = null;

/** Anonymous visitor id: a random UUID kept in this browser (no login, no personal data). */
export function userId(): string {
  try {
    const existing = window.localStorage.getItem(KEY);
    if (existing) return existing;
    const id = crypto.randomUUID();
    window.localStorage.setItem(KEY, id);
    return id;
  } catch {
    memoryId ??= crypto.randomUUID();
    return memoryId;
  }
}

export const USER_HEADER = "X-CineSense-User";

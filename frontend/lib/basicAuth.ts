/** HTTP Basic Auth check for the technical view (/tech): TECH_USER / TECH_PASSWORD from the environment.
 *  Without a configured login everything is allowed (local development). */
export function basicAuthOk(header: string | null, user: string | undefined, password: string | undefined): boolean {
  if (!user || !password) return true;
  if (!header?.startsWith("Basic ")) return false;
  let decoded: string;
  try {
    decoded = atob(header.slice(6).trim());
  } catch {
    return false;
  }
  const colon = decoded.indexOf(":");
  if (colon < 0) return false;
  return same(decoded.slice(0, colon), user) && same(decoded.slice(colon + 1), password);
}

/** Compares without stopping at the first different character (no timing hint). */
function same(a: string, b: string): boolean {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}

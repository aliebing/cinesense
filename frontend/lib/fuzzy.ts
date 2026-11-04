/** Typo-tolerant matching for short lists in the browser (the 1,128 mood tags): no server round trip. */

const norm = (s: string) =>
  s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

/** Edit distance with swapped neighbours counting once ("spcae" -> "space" is 1). */
function distance(a: string, b: string): number {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
    }
  return d[a.length][b.length];
}

const similarity = (a: string, b: string) => 1 - distance(a, b) / Math.max(a.length, b.length);
const MIN_SIMILARITY = 0.7; // one typo in a 4-5 letter word, two in a long one
const MIN_FUZZY_CHARS = 3; // shorter input only matches as written

/** The items that fit `query`, best first: those starting with it, then containing it, then typo-close ones
 *  (to the whole item or one of its words). Ignores case and accents. */
export function fuzzyFind(query: string, items: string[]): string[] {
  const q = norm(query);
  if (!q) return [];
  const scored: { item: string; score: number; order: number }[] = [];
  items.forEach((item, order) => {
    const n = norm(item);
    let score = n.startsWith(q) ? 3 : n.includes(q) ? 2 : 0;
    if (!score && q.length >= MIN_FUZZY_CHARS) {
      const best = Math.max(similarity(q, n), ...n.split(/\s+/).map((w) => similarity(q, w)));
      if (best >= MIN_SIMILARITY) score = best;
    }
    if (score) scored.push({ item, score, order });
  });
  return scored.sort((a, b) => b.score - a.score || a.order - b.order).map((s) => s.item);
}

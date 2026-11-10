import type { MoodFit } from "@/lib/api";
import type { Movie } from "@/lib/types";

/** The ranking's reasons as a readable line: the mood scores ("action 97%") first as one phrase, then the rest
 *  ("with Keanu Reeves", "streaming on Netflix"). */
export function whyText(reasons: string[]): string {
  const moods: string[] = [];
  const rest: string[] = [];
  for (const r of reasons) {
    const m = /^(.+) (\d+)%$/.exec(r);
    if (m) moods.push(`${m[1]} (${m[2]}%)`);
    else rest.push(r);
  }
  const parts = moods.length ? [`Strong on your moods: ${moods.join(", ")}`, ...rest] : rest;
  return parts.join(" · ");
}

const PRESENT = 30; // percent from which a mood counts as present (the ranking's REASON_MIN)
const STRONG = 60; // percent from which it is a strong part of the film
const EXCLUDED_SHOWN = 50; // an excluded mood this strong is pointed out (the search's not-threshold)
const count = new Intl.NumberFormat("en-US");
const rating = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** "Why it fits you" for the film on stage: the search's reasons when it ranked the film; otherwise how the film
 *  carries your moods (`fit`), or, without moods, what it is: one of its world's top-rated films, with the rating. */
export function stageWhyText(m: Movie, worldTitle: string, reasons: string[], fit: MoodFit[] | null): string {
  if (reasons.length) return whyText(reasons);
  const rated = m.ml_rating !== null ? ` · MovieLens ${rating.format(m.ml_rating)}/5 from ${count.format(m.ml_rating_count)} ratings` : "";
  const top = `One of the top-rated ${worldTitle} films${rated}`;
  const wished = (fit ?? []).filter((f) => f.mode !== "not");
  if (!wished.length) return top;
  if (wished.every((f) => f.percent === null)) return `No mood data to compare with your moods · ${top}`;
  const pct = (f: MoodFit) => `${f.tag} (${f.percent}%)`;
  const strong = wished.filter((f) => f.percent !== null && f.percent >= STRONG);
  const partly = wished.filter((f) => f.percent !== null && f.percent >= PRESENT && f.percent < STRONG);
  const weak = wished.filter((f) => f.percent !== null && f.percent < PRESENT);
  const excluded = (fit ?? []).filter((f) => f.mode === "not" && f.percent !== null && f.percent >= EXCLUDED_SHOWN);
  const parts: string[] = [];
  if (strong.length) parts.push(`Strong on your moods: ${strong.map(pct).join(", ")}`);
  if (partly.length) parts.push(`${strong.length ? "partly" : "Partly"} ${partly.map(pct).join(", ")}`);
  if (weak.length) parts.push(`${strong.length || partly.length ? "hardly" : "Not a match for"} ${weak.map(pct).join(", ")}`);
  if (excluded.length) parts.push(`has what you excluded: ${excluded.map(pct).join(", ")}`);
  if (!strong.length) parts.push(top);
  return parts.join(" · ");
}

/** Plain names for the evaluation's keys (backend/cinesense/evaluation). */

export const CHECKS: Record<string, string> = {
  constraints: "Constraints held",
  tools: "Right tools",
  grounding: "Grounded reply",
  availability_claims: "No unconfirmed streaming claim",
  reply: "Expected fact in reply",
  relaxed: "Widened when expected",
  guarded: "Injection guard",
};

/** summary.counts key -> label, in the order the page lists them. */
export const METRICS: [string, string, string][] = [
  ["constraint_satisfaction", "Constraints held", "every film keeps runtime, genre, kind, years, person, rating"],
  ["tool_selection", "Right tools", "an expected tool was called in the final turn, none it must not call"],
  ["grounding", "Grounded reply", "the user only sees films the search returned (after the guard)"],
  ["availability_claims", "No unconfirmed streaming claim", "“streams on …” only when the data says so"],
  ["relaxation", "Widened when expected", "a thin search was widened exactly when the scenario says so"],
  ["guard", "Injection guard", "attacks blocked before the model, harmless wishes about AIs let through"],
  ["reply_checks", "Expected fact in reply", "e.g. “1979” for Alien"],
];

export const RANKERS: Record<string, string> = {
  bayesian: "Baseline A: filters and rating only",
  cosine: "Baseline B: movieFinder (tag cosine)",
  cinesense: "CineSense",
};

/** "2026-11-05_1554" -> "5 Nov 2026, 15:54" */
export function runLabel(run: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})$/.exec(run);
  if (!m) return run;
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(m[2]) - 1];
  return `${Number(m[3])} ${month} ${m[1]}, ${m[4]}:${m[5]}`;
}

/** "anthropic/claude-haiku-5.5" -> "Claude Haiku 5.5" */
export function modelLabel(id: unknown): string | null {
  if (typeof id !== "string" || !id) return null;
  const name = id.split("/").pop() ?? id;
  return name
    .split("-")
    .map((w) => (/^\d/.test(w) ? w : w[0].toUpperCase() + w.slice(1)))
    .join(" ");
}

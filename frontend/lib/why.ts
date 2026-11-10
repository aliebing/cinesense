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

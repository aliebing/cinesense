/** Small formatters of the admin pages. */

export function money(v: number | null | undefined): string {
  if (typeof v !== "number") return "–";
  return `$${v === 0 ? "0" : v < 0.01 ? v.toFixed(4) : v.toFixed(2)}`;
}

export function duration(ms: number | null | undefined): string {
  if (typeof ms !== "number") return "–";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** "5 Nov, 15:54" in the viewer's time zone */
export function when(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

import type { EvalRunOverview } from "@/lib/api";
import { runLabel } from "./labels";

type Point = { run: string; value: number | null; note: string };

const W = 360;
const H = 150;
const PAD = { l: 36, r: 14, t: 14, b: 26 };

/** One measure over the saved runs: a thin line, a marker per run, the chosen run ringed, a tooltip per marker. */
function LineChart({ title, points, min, max, format, selected, onSelect }: {
  title: string;
  points: Point[];
  min: number;
  max: number;
  format: (v: number) => string;
  selected: string;
  onSelect: (run: string) => void;
}) {
  const shown = points.filter((p) => p.value != null) as (Point & { value: number })[];
  const x = (i: number) => PAD.l + (shown.length < 2 ? 0 : (i / (shown.length - 1)) * (W - PAD.l - PAD.r));
  const y = (v: number) => PAD.t + (1 - (v - min) / (max - min)) * (H - PAD.t - PAD.b);
  const ticks = [min, (min + max) / 2, max];
  const path = shown.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const last = shown.at(-1);
  return (
    <figure className="ev-chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title}, one point per run`}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="ev-grid" x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} />
            <text className="ev-axis" x={PAD.l - 6} y={y(t) + 4} textAnchor="end">{format(t)}</text>
          </g>
        ))}
        <path className="ev-line" d={path} />
        {shown.map((p, i) => (
          <g
            key={p.run}
            className={p.run === selected ? "ev-dot is-selected" : "ev-dot"}
            onClick={() => onSelect(p.run)}
            tabIndex={0}
            role="button"
            aria-label={`${runLabel(p.run)}: ${format(p.value)}. ${p.note}. Show this run.`}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(p.run)}
          >
            <title>{`${runLabel(p.run)}: ${format(p.value)} (${p.note})`}</title>
            <circle className="ev-hit" cx={x(i)} cy={y(p.value)} r={12} />
            <circle className="ev-mark" cx={x(i)} cy={y(p.value)} r={p.run === selected ? 5.5 : 4} />
          </g>
        ))}
        {last && (
          <text className="ev-value" x={x(shown.length - 1)} y={y(last.value) - 10} textAnchor="end">
            {format(last.value)}
          </text>
        )}
        <text className="ev-axis" x={PAD.l} y={H - 6}>{shown[0] ? runLabel(shown[0].run).split(",")[0] : ""}</text>
        <text className="ev-axis" x={W - PAD.r} y={H - 6} textAnchor="end">
          {last ? runLabel(last.run).split(",")[0] : ""}
        </text>
      </svg>
    </figure>
  );
}

/** How the evaluation moved across runs, as two small charts (two measures on different scales, never one chart). */
export default function RunHistory({ runs, selected, onSelect }: {
  runs: EvalRunOverview[];
  selected: string;
  onSelect: (run: string) => void;
}) {
  return (
    <div className="ev-history">
      <LineChart
        title="Scenarios passing every check"
        points={runs.map((r) => ({
          run: r.run,
          value: r.scenarios ? (100 * r.passed) / r.scenarios : null,
          note: `${r.passed} of ${r.scenarios}`,
        }))}
        min={0}
        max={100}
        format={(v) => `${Math.round(v)}%`}
        selected={selected}
        onSelect={onSelect}
      />
      <LineChart
        title="Judge score of the agent's top 5 (1–5)"
        points={runs.map((r) => ({ run: r.run, value: r.agent_judge, note: `${r.scenarios} scenarios` }))}
        min={1}
        max={5}
        format={(v) => v.toFixed(1)}
        selected={selected}
        onSelect={onSelect}
      />
    </div>
  );
}

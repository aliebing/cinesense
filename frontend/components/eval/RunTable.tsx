import { money } from "@/components/admin/format";
import type { EvalRunOverview } from "@/lib/api";
import { modelLabel, runLabel } from "./labels";

export const RECENT = 10;

/** The latest runs, newest first: click one to open its full record below. */
export default function RunTable({ runs, selected, onSelect }: { runs: EvalRunOverview[]; selected: string; onSelect: (run: string) => void }) {
  const recent = [...runs].reverse().slice(0, RECENT);
  return (
    <table className="evt">
      <thead>
        <tr>
          <th>Run</th>
          <th>Agent model</th>
          <th>Scenarios</th>
          <th className="num">Passed</th>
          <th className="num">Judge</th>
          <th className="num">Cost</th>
        </tr>
      </thead>
      <tbody>
        {recent.map((r) => (
          <tr key={r.run} className={r.run === selected ? "is-selected" : undefined} onClick={() => onSelect(r.run)}>
            <td>
              <button onClick={() => onSelect(r.run)} aria-current={r.run === selected ? "true" : undefined}>
                {runLabel(r.run)}
              </button>
              {r.source === "server" && <span className="vis-tag">started here</span>}
            </td>
            <td>{modelLabel(r.model) ?? "not recorded"}</td>
            <td>
              {r.scenarios === r.scenarios_total ? `all ${r.scenarios}` : `${r.scenarios} of ${r.scenarios_total}`}
              {r.stopped && " (stopped)"}
            </td>
            <td className="num">
              {r.passed} / {r.scenarios}
            </td>
            <td className="num">{r.agent_judge?.toFixed(2) ?? "–"}</td>
            <td className="num">{r.cost_usd ? money(r.cost_usd) : "–"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

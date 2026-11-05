"use client";

import { useMemo, useState } from "react";
import type { EvalComparisonRow, EvalScenario } from "@/lib/api";
import { CHECKS, RANKERS } from "./labels";

type Filter = "all" | "failed" | "fallback";

/** Every scenario of a run: a row with its checks, judge score and time; opened, the whole turn behind it. */
export default function ScenarioList({ scenarios, rows }: { scenarios: EvalScenario[]; rows: EvalComparisonRow[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [category, setCategory] = useState("");
  const categories = useMemo(() => [...new Set(scenarios.map((s) => s.category))].sort(), [scenarios]);
  const byId = useMemo(() => new Map(rows.map((r) => [r.id, r])), [rows]);
  const failed = scenarios.filter((s) => !s.passed).length;
  const fallbacks = scenarios.filter((s) => s.grounding_fallback).length;
  const shown = scenarios.filter(
    (s) =>
      (!category || s.category === category) &&
      (filter === "all" || (filter === "failed" ? !s.passed : s.grounding_fallback)),
  );

  return (
    <>
      <div className="ev-filters" role="group" aria-label="Filter scenarios">
        {(
          [
            ["all", `All ${scenarios.length}`],
            ["failed", `Failed ${failed}`],
            ["fallback", `Template fallback ${fallbacks}`],
          ] as [Filter, string][]
        ).map(([key, label]) => (
          <button key={key} aria-pressed={filter === key} onClick={() => setFilter(key)}>
            {label}
          </button>
        ))}
        <label>
          Category{" "}
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">all</option>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
      </div>
      {shown.length === 0 && <p className="ev-muted">No scenario matches this filter.</p>}
      <ul className="ev-scenarios">
        {shown.map((s) => (
          <li key={s.id}>
            <details>
              <summary className={s.passed ? undefined : "is-failed"}>
                <span className="ev-status" aria-label={s.passed ? "passed" : "failed"}>
                  {s.passed ? "✓" : "✗"}
                </span>
                <span className="ev-id">
                  {s.id}
                  <small>{s.category}</small>
                </span>
                <span className="ev-wish">{s.turns.join(" → ")}</span>
                <CheckChips checks={s.checks} />
                <span className="ev-num" title={s.judge?.reason}>
                  {s.judge?.score ?? "–"}
                  <small>judge</small>
                </span>
                <span className="ev-num">
                  {s.latency_s.toFixed(1)}
                  <small>s</small>
                </span>
              </summary>
              <Details s={s} row={byId.get(s.id)} />
            </details>
          </li>
        ))}
      </ul>
    </>
  );
}

/** The checks that apply: the passed ones as one chip (named in its tooltip), each failed one by name. */
function CheckChips({ checks }: { checks: EvalScenario["checks"] }) {
  const applying = Object.entries(checks).filter(([, c]) => c.applies);
  const passed = applying.filter(([, c]) => c.ok).map(([key]) => CHECKS[key] ?? key);
  return (
    <span className="ev-checks">
      {passed.length > 0 && (
        <span className="ev-check" title={passed.join(", ")}>
          ✓ {passed.length} {passed.length === 1 ? "check" : "checks"}
        </span>
      )}
      {applying
        .filter(([, c]) => !c.ok)
        .map(([key, c]) => (
          <span key={key} className="ev-check is-bad" title={c.why.join("; ")}>
            ✗ {CHECKS[key] ?? key}
          </span>
        ))}
    </span>
  );
}

function Details({ s, row }: { s: EvalScenario; row?: EvalComparisonRow }) {
  const problems = Object.entries(s.checks).filter(([, c]) => !c.ok);
  const perTurn = s.tools_per_turn ?? [s.tools_called];
  return (
    <div className="ev-detail">
      {s.error && <p className="ev-bad">Error: {s.error}</p>}
      {problems.map(([key, c]) => (
        <p key={key} className="ev-bad">
          {CHECKS[key] ?? key}: {c.why.join("; ")}
        </p>
      ))}
      {s.failure && <p>Injected failure: {s.failure.replace("_", " ")}</p>}
      <h4>Turns and tools</h4>
      <ol>
        {s.turns.map((t, i) => (
          <li key={i}>
            “{t}” <span className="ev-muted">→ {perTurn[i]?.join(", ") || (s.tools_per_turn ? "no tools" : "")}</span>
          </li>
        ))}
      </ol>
      {!s.tools_per_turn && s.turns.length > 1 && (
        <p className="ev-muted">This run saved the tools of all turns together.</p>
      )}
      <h4>Reply{s.grounding_fallback ? " (template: the model's own reply named " + (s.grounding_reason ?? []).join(", ") + ")" : ""}</h4>
      <pre>{s.reply || "(no reply)"}</pre>
      {s.relaxed && s.relaxed.length > 0 && <p>Widened: {s.relaxed.join("; ")}</p>}
      <h4>Films found ({s.results.length})</h4>
      <p>{s.results.join(", ") || "none"}</p>
      {s.judge?.reason && (
        <>
          <h4>Judge ({s.judge.score ?? "–"} of 5)</h4>
          <p>{s.judge.reason}</p>
        </>
      )}
      {row && (
        <>
          <h4>The three rankers on this search</h4>
          <table className="ev-table ev-compare">
            <tbody>
              {Object.keys(row.top).map((n) => (
                <tr key={n} className={n === "cinesense" ? "is-ours" : undefined}>
                  <th scope="row">{RANKERS[n] ?? n}</th>
                  <td>{row.judge[n] ?? "–"}</td>
                  <td>{row.top[n].join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

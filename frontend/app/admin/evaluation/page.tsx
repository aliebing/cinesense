"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import RankerComparison from "@/components/eval/RankerComparison";
import RunHistory from "@/components/eval/RunHistory";
import ScenarioList from "@/components/eval/ScenarioList";
import { METRICS, modelLabel, runLabel } from "@/components/eval/labels";
import { type EvalRun, type EvalRunOverview, getEvalRun, getEvalRuns } from "@/lib/api";
import "../tech.css";
import "./eval.css";

/** The saved `make eval` runs: what passed, how each check did, the ranker comparison, the history, and every
 *  scenario with the turn behind it. Behind the same login as /tech (proxy.ts and the backend both check it). */
export default function EvalPage() {
  const [runs, setRuns] = useState<EvalRunOverview[] | null>(null);
  const [selected, setSelected] = useState("");
  const [run, setRun] = useState<EvalRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvalRuns().then((r) => {
      if (!r.ok) return setError("The evaluation results could not be loaded. Is the backend running?");
      setRuns(r.data);
      if (r.data.length) setSelected(r.data[r.data.length - 1].run);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    getEvalRun(selected).then((r) => (r.ok ? setRun(r.data) : setError(`Run ${selected} could not be loaded.`)));
  }, [selected]);

  return (
    <div className="tech ev">
      <header className="tech-head">
        <strong>CineSense evaluation</strong>
        <span>
          <Link href="/tech">technical view</Link> · <Link href="/">back to the app</Link>
        </span>
      </header>
      {error && <p className="tech-error">{error}</p>}
      {runs && runs.length === 0 && (
        <p className="ev-muted">
          No saved runs. Run <code>make eval</code>; on the server, mount the results folder at CINESENSE_EVAL_DIR.
        </p>
      )}
      {runs && runs.length > 0 && (
        <label className="ev-run">
          Run{" "}
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            {[...runs].reverse().map((r) => (
              <option key={r.run} value={r.run}>
                {runLabel(r.run)}: {r.passed} of {r.scenarios} passed
              </option>
            ))}
          </select>
        </label>
      )}
      {run && run.run === selected && <RunView run={run} runs={runs ?? []} onSelect={setSelected} />}
    </div>
  );
}

function RunView({ run, runs, onSelect }: { run: EvalRun; runs: EvalRunOverview[]; onSelect: (r: string) => void }) {
  const s = run.summary as Record<string, number | string | undefined> & { counts?: Record<string, [number, number]> };
  const counts = s.counts ?? {};
  const fallbacks = Number(s.grounding_fallbacks ?? 0);
  const agent = modelLabel(s.agent_model);
  const judge = modelLabel(s.judge_model);
  const failed = run.scenarios - run.passed;
  const money = (v: unknown) => (typeof v === "number" ? `$${v < 0.01 ? v.toFixed(4) : v.toFixed(2)}` : "–");

  return (
    <>
      <section className="ev-hero" aria-label="Result">
        <p className="ev-score">
          <span className="ev-big">{run.passed}</span> of {run.scenarios} scenarios pass every check
        </p>
        <p className="ev-muted">
          Run of {runLabel(run.run)}.{" "}
          {agent ? `The agent is ${agent}` : "The agent model was not recorded"}
          {judge ? `, the judge ${judge}` : ""}. Every scenario runs through the real agent and catalogue; streaming
          comes from the cache only. {failed ? `${failed} failed, listed below.` : "None failed."}
        </p>
        <dl className="ev-facts">
          <div>
            <dt>Median time per scenario</dt>
            <dd>{typeof s.latency_median_s === "number" ? `${s.latency_median_s.toFixed(1)} s` : "–"}</dd>
          </div>
          <div>
            <dt>90% finish within</dt>
            <dd>{typeof s.latency_p90_s === "number" ? `${s.latency_p90_s.toFixed(1)} s` : "–"}</dd>
          </div>
          <div>
            <dt>Cost per chat turn</dt>
            <dd>{money(s.cost_per_turn_usd)}</dd>
          </div>
          <div>
            <dt>Judge score, agent&apos;s top 5</dt>
            <dd>{run.agent_judge?.toFixed(2) ?? "–"}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="ev-checks">
        <h2 id="ev-checks">Automatic checks</h2>
        <p className="ev-lead">Each check counts only the scenarios that define it.</p>
        <ul className="ev-metrics">
          {METRICS.filter(([key]) => counts[key]).map(([key, label, hint]) => {
            const [k, n] = counts[key];
            return <MetricBar key={key} label={label} hint={hint} k={k} n={n} />;
          })}
          {counts.grounding && (
            <MetricBar
              label="Grounded before the guard"
              hint="the model's own reply named only returned films; otherwise a template answer was shown"
              k={counts.grounding[1] - fallbacks}
              n={counts.grounding[1]}
              soft
            />
          )}
        </ul>
      </section>

      <section aria-labelledby="ev-rankers">
        <h2 id="ev-rankers">Ranking comparison</h2>
        <RankerComparison run={run} />
      </section>

      {runs.length > 1 && (
        <section aria-labelledby="ev-history">
          <h2 id="ev-history">History</h2>
          <p className="ev-lead">
            Scenarios were added between runs ({runs[0].scenarios} in the first, {runs.at(-1)?.scenarios} in the
            latest), so the rates are not over the same set. Click a point to show that run.
          </p>
          <RunHistory runs={runs} selected={run.run} onSelect={onSelect} />
        </section>
      )}

      <section aria-labelledby="ev-scenarios">
        <h2 id="ev-scenarios">Scenarios</h2>
        <ScenarioList scenarios={run.results} rows={run.comparison.rows ?? []} />
      </section>
    </>
  );
}

function MetricBar({ label, hint, k, n, soft = false }: { label: string; hint: string; k: number; n: number; soft?: boolean }) {
  const full = k === n;
  return (
    <li className={full ? "ev-metric" : soft ? "ev-metric is-soft" : "ev-metric is-short"}>
      <span className="ev-metric-label">
        {label}
        <small>{hint}</small>
      </span>
      <span className="ev-metric-track" aria-hidden="true">
        <span className="ev-metric-fill" style={{ width: `${n ? (100 * k) / n : 0}%` }} />
      </span>
      <span className="ev-metric-value">
        {k} / {n}
      </span>
    </li>
  );
}

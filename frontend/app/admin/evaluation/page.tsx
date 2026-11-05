"use client";

import { useCallback, useEffect, useState } from "react";
import LiveRun from "@/components/eval/LiveRun";
import RankerComparison from "@/components/eval/RankerComparison";
import RunHistory from "@/components/eval/RunHistory";
import RunLauncher from "@/components/eval/RunLauncher";
import RunTable, { RECENT } from "@/components/eval/RunTable";
import ScenarioList from "@/components/eval/ScenarioList";
import { METRICS, modelLabel, runLabel } from "@/components/eval/labels";
import {
  type ApiResult,
  type EvalLive,
  type EvalOptions,
  type EvalRun,
  type EvalRunOverview,
  getEvalLive,
  getEvalOptions,
  getEvalRun,
  getEvalRuns,
  startEval,
  stopEval,
} from "@/lib/api";

import "./eval.css";

/** The evaluation: start a run (model, scenarios, estimated cost) and watch it live, the last runs, and one run
 *  in full: what passed, each check, the ranker comparison, the history and every scenario with its turns.
 *  Behind the admin login (proxy.ts and the backend both check it). */
export default function EvalPage() {
  const [runs, setRuns] = useState<EvalRunOverview[] | null>(null);
  const [selected, setSelected] = useState("");
  const [run, setRun] = useState<EvalRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<EvalOptions | null>(null);
  const [live, setLive] = useState<EvalLive | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const running = live?.status === "running" || live?.status === "stopping";

  const showRuns = useCallback((r: ApiResult<EvalRunOverview[]>, pick?: string) => {
    if (!r.ok) return setError("The evaluation results could not be loaded. Is the backend running?");
    setRuns(r.data);
    setSelected((cur) => pick ?? (cur || r.data.at(-1)?.run || ""));
  }, []);
  const loadRuns = useCallback((pick?: string) => getEvalRuns().then((r) => showRuns(r, pick)), [showRuns]);

  useEffect(() => {
    getEvalRuns().then((r) => showRuns(r));
    getEvalOptions().then((r) => r.ok && setOptions(r.data));
    getEvalLive().then((r) => r.ok && r.data.status !== "idle" && setLive(r.data));
  }, [showRuns]);

  // while a run goes, ask for its state every 1.5 s; when it is saved, list it and open it
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(async () => {
      const r = await getEvalLive();
      if (!r.ok) return;
      setLive(r.data);
      if (r.data.run) void loadRuns(r.data.run);
    }, 1500);
    return () => clearInterval(timer);
  }, [running, loadRuns]);

  useEffect(() => {
    if (!selected) return;
    getEvalRun(selected).then((r) => (r.ok ? setRun(r.data) : setError(`Run ${selected} could not be loaded.`)));
  }, [selected]);

  const start = async (model: string, ids: string[]) => {
    setStartError(null);
    const r = await startEval(model, ids);
    if (r.ok) setLive(r.data);
    else setStartError(r.message ?? "The run could not be started.");
  };
  const stop = async () => {
    const r = await stopEval();
    if (r.ok) setLive(r.data);
  };
  const full = (runs ?? []).filter((r) => r.scenarios === r.scenarios_total && !r.stopped);

  return (
    <div className="ev">
      <section aria-labelledby="ev-start">
        <h2 id="ev-start">Start a run</h2>
        <p className="ev-lead">
          Every scenario runs through the real agent and catalogue with the chosen model; streaming comes from the
          cache only. Each answer is checked automatically and scored by the judge as soon as it is in.
        </p>
        {options ? (
          <RunLauncher options={options} busy={running} onStart={start} />
        ) : (
          <p className="ev-muted">Loading models and scenarios…</p>
        )}
        {startError && <p className="tech-error">{startError}</p>}
        {live && live.status !== "idle" && <LiveRun live={live} onStop={stop} onShow={setSelected} />}
      </section>

      {error && <p className="tech-error">{error}</p>}
      {runs && runs.length === 0 && <p className="ev-muted">No saved runs yet.</p>}
      {runs && runs.length > 0 && (
        <section aria-labelledby="ev-recent">
          <h2 id="ev-recent">Last {Math.min(RECENT, runs.length)} runs</h2>
          <RunTable runs={runs} selected={selected} onSelect={setSelected} />
        </section>
      )}
      {run && run.run === selected && <RunView run={run} runs={full} onSelect={setSelected} />}
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
      <h2 id="ev-run">Run of {runLabel(run.run)}</h2>
      <section className="ev-hero" aria-labelledby="ev-run">
        <p className="ev-score">
          <span className="ev-big">{run.passed}</span> of {run.scenarios} scenarios pass every check
          {run.scenarios < run.scenarios_total && (
            <span className="ev-muted"> (a selection of {run.scenarios_total})</span>
          )}
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
          <h2 id="ev-history">History of full runs</h2>
          <p className="ev-lead">
            Only runs of every scenario. Scenarios were added between runs ({runs[0].scenarios} in the first,{" "}
            {runs.at(-1)?.scenarios} in the latest), so the rates are not over the same set. Click a point to show
            that run.
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

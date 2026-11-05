import { money } from "@/components/admin/format";
import type { EvalLive } from "@/lib/api";
import { CHECKS, modelLabel, runLabel } from "./labels";

/** The run in progress (or just finished): progress, the scenario being asked, each result as it comes in. */
export default function LiveRun({ live, onStop, onShow }: { live: EvalLive; onStop: () => void; onShow: (run: string) => void }) {
  const total = live.total ?? 0;
  const done = live.done ?? 0;
  const running = live.status === "running" || live.status === "stopping";
  const results = [...(live.results ?? [])].reverse();
  return (
    <section className="evr" aria-live="polite" aria-label="Current run">
      <div className="evr-head">
        <strong>
          {running ? "Running" : live.status === "done" ? "Finished" : live.status === "stopped" ? "Stopped" : "Failed"}:{" "}
          {done} of {total} scenarios with {modelLabel(live.model) ?? live.model}
        </strong>
        <span className="admin-lead">
          {live.passed ?? 0} passed · agent cost {running ? "so far " : ""}
          {money(live.cost_usd ?? 0)}
        </span>
        {live.status === "running" && <button onClick={onStop}>Stop after this scenario</button>}
        {live.status === "stopping" && <span className="admin-lead">Stopping after this scenario…</span>}
        {live.run && (
          <button onClick={() => onShow(live.run as string)}>Show the saved run of {runLabel(live.run)}</button>
        )}
      </div>
      <div className="evr-track" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
        <span style={{ width: `${total ? (100 * done) / total : 0}%` }} />
      </div>
      {live.error && <p className="tech-error">{live.error}</p>}
      {live.current && (
        <p className="evr-now">
          Asking <b>{live.current.id}</b>: “{live.current.turns.join(" → ")}”
        </p>
      )}
      {live.phase === "comparing" && running && <p className="evr-now">Comparing CineSense with the two baseline rankers…</p>}
      <ul className="evr-list">
        {results.map((r) => (
          <li key={r.id} className={r.passed ? "" : "is-failed"}>
            <span className="ev-status" aria-label={r.passed ? "passed" : "failed"}>
              {r.passed ? "✓" : "✗"}
            </span>
            <div>
              <p className="evr-wish">
                <b>{r.id}</b> “{r.turns.join(" → ")}”
                <span className="admin-lead">
                  {" "}
                  · {r.latency_s?.toFixed(1)} s · {money(r.cost_usd)}
                  {r.judge?.score != null && <> · judge {r.judge.score}/5</>}
                </span>
              </p>
              {r.error && <p className="tech-error">{r.error}</p>}
              {r.failed_checks.length > 0 && (
                <p className="ev-bad">Failed: {r.failed_checks.map((c) => CHECKS[c] ?? c).join(", ")}</p>
              )}
              <p className="evr-reply">{r.reply.replace(/\*\*/g, "")}</p>
              {r.results.length > 0 && <p className="admin-lead">Films: {r.results.join(", ")}</p>}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

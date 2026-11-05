import type { EvalRun } from "@/lib/api";
import { RANKERS } from "./labels";

const ORDER = ["bayesian", "cosine", "cinesense"];

/** The three rankers on the agent's criteria: the judge's mean score as bars (0-5), the objective measures below. */
export default function RankerComparison({ run }: { run: EvalRun }) {
  const names = ORDER.filter((n) => run.rankers[n]);
  if (!names.length) return <p className="ev-muted">This run has no ranking comparison.</p>;
  const n = run.comparison.rows?.length ?? 0;
  return (
    <>
      <p className="ev-lead">
        The same {n} mood searches, with the criteria the agent set and identical hard filters, ranked three ways.
        The judge sees only titles and years.
      </p>
      <div className="ev-bars" role="list" aria-label="Mean judge score per ranker">
        {names.map((name) => {
          const v = run.rankers[name].judge;
          return (
            <div key={name} role="listitem" className={name === "cinesense" ? "ev-bar is-ours" : "ev-bar"}>
              <span className="ev-bar-name">{RANKERS[name] ?? name}</span>
              <span className="ev-bar-track" title={v == null ? "no score" : `${v.toFixed(2)} of 5`}>
                <span className="ev-bar-fill" style={{ width: `${((v ?? 0) / 5) * 100}%` }} />
              </span>
              <span className="ev-bar-value">{v == null ? "–" : v.toFixed(2)}</span>
            </div>
          );
        })}
      </div>
      <table className="ev-table">
        <thead>
          <tr>
            <th scope="col">Ranker</th>
            <th scope="col" title="weighted mean relevance of the wanted tags in the top 10 (what CineSense ranks by)">
              Tag relevance@10
            </th>
            <th scope="col" title="cosine to the wanted tags (what movieFinder ranks by)">Tag cosine@10</th>
            <th scope="col" title="mean of each search's median MovieLens rating count: how well known the picks are">
              Rating count
            </th>
          </tr>
        </thead>
        <tbody>
          {names.map((name) => {
            const m = run.rankers[name];
            return (
              <tr key={name} className={name === "cinesense" ? "is-ours" : undefined}>
                <th scope="row">{RANKERS[name] ?? name}</th>
                <td>{m.tag_relevance?.toFixed(2) ?? "–"}</td>
                <td>{m.tag_cosine?.toFixed(2) ?? "–"}</td>
                <td>{m.median_rating_count != null ? Math.round(m.median_rating_count).toLocaleString("en") : "–"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import VisitorDetail from "@/components/admin/VisitorDetail";
import { duration, money, when } from "@/components/admin/format";
import { type ApiResult, getVisitors, type VisitorPage } from "@/lib/api";
import "./visitors.css";

const LIMIT = 50;
type Scope = "chat" | "tech" | null;
const SCOPES: [Scope, string][] = [
  [null, "All"],
  ["chat", "Chat"],
  ["tech", "Tech view"],
];

/** The visitor log: every agent turn of the last 30 days, newest first; click one for everything behind it. */
export default function VisitorsPage() {
  const [scope, setScope] = useState<Scope>(null);
  const [page, setPage] = useState<VisitorPage | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  const show = useCallback((r: ApiResult<VisitorPage>, offset: number) => {
    if (!r.ok) return setError("The visitor log could not be loaded. Is the backend running?");
    setError(null);
    setPage((p) => (offset > 0 && p ? { ...r.data, items: [...p.items, ...r.data.items] } : r.data));
    if (offset === 0) setSelected(r.data.items[0]?.id ?? null);
  }, []);

  useEffect(() => {
    const n = ++seq.current;
    getVisitors(scope, 0, LIMIT).then((r) => n === seq.current && show(r, 0));
  }, [scope, show]);

  const more = (offset: number) => {
    const n = ++seq.current;
    getVisitors(scope, offset, LIMIT).then((r) => n === seq.current && show(r, offset));
  };

  return (
    <div className="vis">
      <p className="admin-lead">
        Every assistant turn of the last 30 days, newest first. Visitors and conversations are short keyed hashes,
        never addresses; entries are deleted after 30 days.
      </p>
      <div className="vis-bar" role="group" aria-label="Show">
        {SCOPES.map(([s, label]) => (
          <button key={label} aria-pressed={scope === s} onClick={() => setScope(s)}>
            {label}
          </button>
        ))}
        {page && (
          <span className="vis-sums">
            {page.sums.count} {page.sums.count === 1 ? "turn" : "turns"}
            {scope !== "tech" && (
              <>
                {" "}
                from {page.sums.visitors} {page.sums.visitors === 1 ? "visitor" : "visitors"} in the chat
              </>
            )} · {money(page.sums.cost_usd)} ·{" "}
            {duration(page.sums.avg_duration_ms)} on average
          </span>
        )}
      </div>
      {error && <p className="tech-error">{error}</p>}
      {page && page.items.length === 0 && <p className="admin-lead">No turns logged yet.</p>}
      {page && page.items.length > 0 && (
        <div className="vis-cols">
          <div className="vis-table-wrap">
            <table className="vis-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Visitor</th>
                  <th>Message</th>
                  <th className="num">Films</th>
                  <th>Tools</th>
                  <th className="num">Tokens</th>
                  <th className="num">Cost</th>
                  <th className="num">Time taken</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((t) => (
                  <tr
                    key={t.id}
                    className={selected === t.id ? "is-selected" : undefined}
                    onClick={() => setSelected(t.id)}
                  >
                    <td className="nowrap">{when(t.ts)}</td>
                    <td>
                      <code>{t.visitor?.slice(0, 6) ?? "–"}</code>
                      {t.scope === "tech" && <span className="vis-tag">tech</span>}
                    </td>
                    <td className="vis-msg">
                      <button onClick={() => setSelected(t.id)} aria-label={`Show turn ${t.id}`}>
                        {t.message ?? "–"}
                      </button>
                    </td>
                    <td className="num">{t.films}</td>
                    <td className="vis-tools">{t.tools.join(", ") || "–"}</td>
                    <td className="num">{(t.input_tokens + t.output_tokens).toLocaleString("en")}</td>
                    <td className="num">{money(t.cost_usd)}</td>
                    <td className="num">{duration(t.duration_ms)}</td>
                    <td className="vis-note">
                      {t.error ? `✗ ${t.error}` : t.guarded ? "guard" : t.grounding_fallback ? "template" : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {page.items.length < page.total && (
              <button className="vis-more" onClick={() => more(page.items.length)}>
                Show {Math.min(LIMIT, page.total - page.items.length)} more
              </button>
            )}
          </div>
          {selected !== null && <VisitorDetail id={selected} />}
        </div>
      )}
    </div>
  );
}

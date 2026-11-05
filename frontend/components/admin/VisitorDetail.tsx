"use client";

import { useEffect, useState } from "react";
import { duration, money, when } from "@/components/admin/format";
import { modelLabel } from "@/components/eval/labels";
import { getVisitorTurn, type VisitorTurnDetail } from "@/lib/api";

/** One logged turn in full: the conversation before it, the message, the reply, criteria, films and tools. */
export default function VisitorDetail({ id }: { id: number }) {
  // the loaded turn is kept with its id, so a newly selected row shows "Loading…" until its own data is in
  const [loaded, setLoaded] = useState<{ id: number; turn: VisitorTurnDetail | null } | null>(null);

  useEffect(() => {
    let live = true;
    getVisitorTurn(id).then((r) => {
      if (live) setLoaded({ id, turn: r.ok ? r.data : null });
    });
    return () => {
      live = false;
    };
  }, [id]);

  const current = loaded?.id === id ? loaded : null;
  const turn = current?.turn ?? null;
  if (current && !turn) return <aside className="vis-detail tech-error">This turn could not be loaded.</aside>;
  if (!turn) return <aside className="vis-detail admin-lead">Loading…</aside>;
  return (
    <aside className="vis-detail" aria-label="Turn details">
      <p className="admin-lead">
        {when(turn.ts)} · {turn.scope === "tech" ? "tech view" : "chat"} · {modelLabel(turn.model) ?? "model unknown"}{" "}
        · {(turn.input_tokens + turn.output_tokens).toLocaleString("en")} tokens · {money(turn.cost_usd)} ·{" "}
        {duration(turn.duration_ms)}
      </p>
      {turn.conversation.length > 0 && (
        <>
          <h2>Earlier in this conversation</h2>
          <ol className="vis-convo">
            {turn.conversation.map((c) => (
              <li key={c.id}>{c.message}</li>
            ))}
          </ol>
        </>
      )}
      <h2>Message</h2>
      <pre>{turn.message}</pre>
      <h2>Reply</h2>
      {turn.error ? <p className="tech-error">The turn failed: {turn.error}</p> : <pre>{turn.reply}</pre>}
      {turn.guarded && <p className="tech-note">The injection guard answered this message.</p>}
      {turn.grounding_fallback && (
        <p className="tech-note">
          Template answer: the model named films outside the results ({turn.grounding_reason.join(", ") || "?"}).
        </p>
      )}
      {turn.criteria_summary && (
        <>
          <h2>Understood as</h2>
          <pre>{turn.criteria_summary}</pre>
        </>
      )}
      {turn.relaxed.length > 0 && <p className="admin-lead">Widened: {turn.relaxed.join("; ")}</p>}
      <h2>Films shown</h2>
      {turn.films.length ? (
        <ol>
          {turn.films.map((f, i) => (
            <li key={`${f.title}-${i}`}>
              {f.title}
              {f.year ? ` (${f.year})` : ""}
              {typeof f.match === "number" ? <span className="admin-lead"> · {f.match}%</span> : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="admin-lead">None.</p>
      )}
      <h2>Tool calls</h2>
      {turn.tools.length ? (
        turn.tools.map((t, i) => (
          <pre key={i}>
            {t.name}({JSON.stringify(t.args)})
          </pre>
        ))
      ) : (
        <p className="admin-lead">None.</p>
      )}
    </aside>
  );
}

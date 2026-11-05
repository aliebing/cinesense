"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { type InspectFilm, inspectTurn, type InspectResult } from "@/lib/api";
import { type Criteria, emptyCriteria } from "@/lib/searchState";
import { shorten } from "@/lib/text";
import { randomId } from "@/lib/user";
import "./tech.css";

/** "directed by … · with …", leaving out what the catalogue doesn't know. */
function credits(f: InspectFilm): string {
  return [
    f.directors.length ? `directed by ${f.directors.join(", ")}` : "",
    f.cast.length ? `with ${f.cast.slice(0, 4).join(", ")}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Technical review page: one plain view of what the agent did — reply, criteria, tools, prompts, tokens, cost —
 *  and the ranked films as text. No pictures, trailers or animation. Its own conversation, separate from the app. */
export default function TechPage() {
  const threadId = useRef<string | null>(null); // created on the first send: no random value while prerendering
  const [criteria, setCriteria] = useState<Criteria>(emptyCriteria);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turn, setTurn] = useState<InspectResult | null>(null);
  const [asked, setAsked] = useState("");

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = message.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    threadId.current ??= `tech-${randomId()}`;
    const r = await inspectTurn(threadId.current, text, criteria);
    setBusy(false);
    if (!r.ok && r.error === "limited" && r.message) return setError(r.message);
    if (!r.ok) return setError("The agent is unavailable (no API key, or the backend is down).");
    setTurn(r.data);
    setAsked(text);
    setCriteria(r.data.criteria); // follow-up questions refine this search, as in the app
    setMessage("");
  };
  const reset = () => {
    threadId.current = null;
    setCriteria(emptyCriteria());
    setTurn(null);
    setAsked("");
  };

  return (
    <div className="tech">
      <header className="tech-head">
        <strong>CineSense · technical view</strong>
        <span>
          <Link href="/">back to the app</Link> · <button onClick={reset}>new conversation</button>
        </span>
      </header>
      <form className="tech-ask" onSubmit={send}>
        <input
          aria-label="Message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="e.g. something funny or action, Marvel welcome, no horror"
        />
        <button type="submit" disabled={busy}>
          {busy ? "running…" : "send"}
        </button>
      </form>
      {error && <p className="tech-error">{error}</p>}
      {turn && (
        <div className="tech-cols">
          <section className="tech-left" aria-label="Explanation">
            <h2>Wish</h2>
            <p>{asked}</p>
            <h2>Agent reply ({turn.picks} picks)</h2>
            <pre className="tech-reply">{turn.reply}</pre>
            {turn.grounding_fallback && (
              <p className="tech-note">Grounding check replaced the model&apos;s text: {turn.grounding_reason.join(", ")}</p>
            )}
            <h2>Search criteria</h2>
            <table>
              <tbody>
                {turn.tags.map((t) => (
                  <tr key={t.tag}>
                    <td>{t.tag}</td>
                    <td>weight {t.weight}</td>
                    <td>{t.mode}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <pre>{turn.criteria_summary}</pre>
            {turn.proposals.length > 0 && <p>Proposed (not applied): {turn.proposals.map((p) => `${p.tag} (${p.mode})`).join(", ")}</p>}
            <h2>Tool calls ({turn.tools.length}, {turn.rounds} rounds)</h2>
            <ol>
              {turn.tools.map((t, i) => (
                <li key={i}>
                  <code>{t.name}</code>
                  <pre>{JSON.stringify(t.args, null, 2)}</pre>
                  {t.result && <pre className="tech-result">→ {t.result}</pre>}
                </li>
              ))}
            </ol>
            <h2>Model, tokens, cost</h2>
            <table>
              <tbody>
                <tr><td>model</td><td>{turn.model}</td></tr>
                <tr><td>input tokens</td><td>{turn.usage.input_tokens ?? 0}</td></tr>
                <tr><td>output tokens</td><td>{turn.usage.output_tokens ?? 0}</td></tr>
                <tr><td>cost</td><td>${turn.cost_usd.toFixed(5)}</td></tr>
                <tr><td>latency</td><td>{turn.latency_s} s</td></tr>
              </tbody>
            </table>
            <h2>Prompts sent</h2>
            <details>
              <summary>agent system prompt</summary>
              <pre>{turn.prompts.agent ?? "—"}</pre>
            </details>
            <details>
              <summary>explain system prompt</summary>
              <pre>{turn.prompts.explain ?? "— (no search ran this turn)"}</pre>
            </details>
            <details>
              <summary>explain input (wish, criteria, results)</summary>
              <pre>{turn.prompts.explain_input ?? "—"}</pre>
            </details>
          </section>
          <section className="tech-right" aria-label="Films">
            <h2>Films ({turn.results.length}; the first {turn.picks} are the reply&apos;s picks) · click a title for its IMDb page</h2>
            <ol>
              {turn.results.map((f, i) => (
                <li key={f.id} className={i < turn.picks ? "is-pick" : ""}>
                  {f.imdb_id ? (
                    <a href={`https://www.imdb.com/de/title/${f.imdb_id}/`} target="_blank" rel="noreferrer" className="tech-film">
                      {f.title}
                      {f.year ? ` (${f.year})` : ""}
                    </a>
                  ) : (
                    <Link href={`/world/${f.worlds[0] ?? "suspense"}?film=${f.id}`} className="tech-film">
                      {f.title}
                      {f.year ? ` (${f.year})` : ""}
                    </Link>
                  )}
                  {f.overview && (
                    <div className="tech-plot" data-testid="tech-short">
                      {shorten(f.overview)}
                    </div>
                  )}
                  <details className="tech-film-details">
                    <summary>details</summary>
                    <div>
                      {f.match_percent}% match, score {f.score?.toFixed(3)}
                    </div>
                    <div>why: {f.reasons.join(" · ") || "—"}</div>
                    <div>
                      {f.genres.join(", ")} · worlds: {f.worlds.join(", ")}
                      {f.runtime_min ? ` · ${f.runtime_min} min` : ""}
                      {f.ml_rating ? ` · MovieLens ${f.ml_rating.toFixed(2)} (${f.ml_rating_count} ratings)` : ""}
                    </div>
                    {credits(f) && <div>{credits(f)}</div>}
                  </details>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </div>
  );
}

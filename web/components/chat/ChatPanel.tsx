"use client";

import { useSearchState, withNoHorror } from "@/lib/searchState";

/** Chat window. The quick filters write the shared search state; Plan 3 switches mode to "live". */
export default function ChatPanel({ mode, horrorIdx = null }: { mode: "static" | "live"; horrorIdx?: number | null }) {
  const disabled = mode === "static";
  const [criteria, setCriteria] = useSearchState();
  const noHorror = criteria.exclude_genres.includes("Horror");
  const quick = [
    {
      label: "🎬 In cinemas",
      on: criteria.availability === "cinema",
      toggle: () => setCriteria({ ...criteria, availability: criteria.availability === "cinema" ? "any" : "cinema" }),
    },
    {
      label: "📺 Streaming",
      on: criteria.availability === "stream",
      toggle: () => setCriteria({ ...criteria, availability: criteria.availability === "stream" ? "any" : "stream" }),
    },
    {
      label: "🚫 No horror",
      on: noHorror,
      toggle: () =>
        setCriteria(
          noHorror
            ? {
                ...criteria,
                exclude_genres: criteria.exclude_genres.filter((g) => g !== "Horror"),
                tags: criteria.tags.filter((t) => !(t.idx === horrorIdx && t.mode === "not")),
              }
            : withNoHorror(criteria, horrorIdx),
        ),
    },
  ];
  return (
    <div className="chat-panel">
      <div className="chat-msg chat-msg--user">Something funny or action, Marvel is welcome, but no horror.</div>
      <div className="chat-msg chat-msg--bot">
        Example: this is where the agent will reply and suggest matching films with reasons.
      </div>
      <form className="chat-input" onSubmit={(e) => e.preventDefault()}>
        <input
          id="chat-input"
          aria-label="Message CineSense"
          placeholder="e.g. “like Interstellar, but shorter”"
          disabled={disabled}
        />
        <button type="submit" aria-label="Send" disabled={disabled}>
          ➤
        </button>
      </form>
      {disabled && <p className="chat-hint">The chat agent is coming soon</p>}
      <div className="chat-chips">
        {quick.map((q) => (
          <button key={q.label} type="button" aria-pressed={q.on} className={q.on ? "is-on" : ""} onClick={q.toggle}>
            {q.label}
          </button>
        ))}
      </div>
    </div>
  );
}

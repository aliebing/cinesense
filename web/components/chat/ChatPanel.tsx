"use client";

const CHIPS = ["🎬 In cinemas", "📺 Streaming", "🚫 No horror"];

/** Chat window. Plan 1 ships the static form; Plan 3 switches mode to "live". */
export default function ChatPanel({ mode }: { mode: "static" | "live" }) {
  const disabled = mode === "static";
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
        {CHIPS.map((c) => (
          <span key={c}>{c}</span>
        ))}
      </div>
    </div>
  );
}

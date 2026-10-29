"use client";

const CHIPS = ["🎬 Läuft im Kino", "📺 Im Stream", "🇬🇧 Englisch", "🚫 Kein Grusel"];

/** Chat window. Plan 1 ships the static form; Plan 3 switches mode to "live". */
export default function ChatPanel({ mode }: { mode: "static" | "live" }) {
  const disabled = mode === "static";
  return (
    <div className="chat-panel">
      <div className="chat-msg chat-msg--user">Was Lustiges oder Action auf Englisch, gern Marvel, aber kein Grusel.</div>
      <div className="chat-msg chat-msg--bot">
        Beispiel: So wird der Agent antworten und dir passende Filme mit Begründung vorschlagen.
      </div>
      <form className="chat-input" onSubmit={(e) => e.preventDefault()}>
        <input
          id="chat-input"
          aria-label="Nachricht an CineSense"
          placeholder="z. B. „wie Interstellar, aber kürzer“"
          disabled={disabled}
        />
        <button type="submit" aria-label="Senden" disabled={disabled}>
          ➤
        </button>
      </form>
      {disabled && <p className="chat-hint">Der Chat-Agent folgt in Kürze</p>}
      <div className="chat-chips">
        {CHIPS.map((c) => (
          <span key={c}>{c}</span>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import ChatResults from "@/components/chat/ChatResults";
import {
  ChatError,
  getChatLog,
  type Proposal,
  setChatStatus,
  streamChat,
  threadId,
  useChatLog,
  useChatStatus,
} from "@/lib/chat";
import { useSearchState, withNoHorror } from "@/lib/searchState";
import type { Movie } from "@/lib/types";

/** Chat window. Live mode talks to the agent; its criteria land in the shared search state (the chips),
 *  and the conversation follows the visitor from the homepage into the genre drawer. `showPicks={false}` leaves
 *  the films out of the replies, for the homepage, which deals them as cards beside the chat. */
export default function ChatPanel({
  mode,
  horrorIdx = null,
  showPicks = true,
}: {
  mode: "static" | "live";
  horrorIdx?: number | null;
  showPicks?: boolean;
}) {
  const live = mode === "live";
  const router = useRouter();
  const [criteria, setCriteria] = useSearchState();
  const [entries, setEntries] = useChatLog();
  const [draft, setDraft] = useState("");
  const status = useChatStatus();
  const busy = status !== null;
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo?.({ top: logRef.current.scrollHeight });
  }, [entries, status]);

  const send = async () => {
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    setEntries([...getChatLog(), { role: "user", text }]);
    setChatStatus("Thinking…");
    try {
      const out = await streamChat({ threadId: threadId(), message: text, criteria }, setChatStatus);
      setCriteria(out.criteria);
      setEntries([
        ...getChatLog(),
        { role: "bot", text: out.reply, results: out.results, proposals: out.proposals, handoff: out.handoff },
      ]);
    } catch (e) {
      setEntries([...getChatLog(), { role: "bot", text: e instanceof ChatError ? e.message : String(e), error: true }]);
    } finally {
      setChatStatus(null);
    }
  };

  const applyProposal = (entryIndex: number, p: Proposal) => {
    setCriteria({ ...criteria, tags: [...criteria.tags.filter((t) => t.idx !== p.idx), { idx: p.idx, weight: 5, mode: "not" }] });
    setEntries(
      entries.map((e, i) =>
        i === entryIndex && e.role === "bot" ? { ...e, proposals: (e.proposals ?? []).filter((x) => x.idx !== p.idx) } : e,
      ),
    );
  };

  const openMovie = (m: Movie) => router.push(`/world/${m.world_ids[0] ?? "suspense"}?film=${m.id}`);
  const lastBot = entries.map((e) => e.role).lastIndexOf("bot");
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
      {!live && (
        <>
          <div className="chat-msg chat-msg--user">Something funny or action, Marvel is welcome, but no horror.</div>
          <div className="chat-msg chat-msg--bot">
            Example: this is where the agent will reply and suggest matching films with reasons.
          </div>
        </>
      )}
      {live && (entries.length > 0 || status) && (
        <div className="chat-log" ref={logRef} aria-live="polite">
          {entries.map((e, i) =>
            e.role === "user" ? (
              <div key={i} className="chat-msg chat-msg--user">
                {e.text}
              </div>
            ) : (
              <div key={i} className={`chat-msg chat-msg--bot${e.error ? " chat-msg--error" : ""}`}>
                <Reply text={e.text} />
                {showPicks && i === lastBot && e.results && e.results.length > 0 && <ChatResults results={e.results} onOpen={openMovie} />}
                {i === lastBot && (e.proposals ?? []).length > 0 && (
                  <div className="chat-proposals">
                    Also exclude:{" "}
                    {e.proposals!.map((p) => (
                      <button key={p.idx} type="button" aria-label={`Also exclude ${p.tag}`} disabled={busy} onClick={() => applyProposal(i, p)}>
                        🚫 {p.tag} +
                      </button>
                    ))}
                  </div>
                )}
                {i === lastBot && e.handoff && (
                  <button
                    type="button"
                    className="chat-handoff"
                    onClick={() => router.push(`/world/${e.handoff!.world_id}?film=${e.handoff!.film_id}`)}
                  >
                    Show on stage →
                  </button>
                )}
              </div>
            ),
          )}
          {status && <p className="chat-status">{status}</p>}
        </div>
      )}
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          id="chat-input"
          aria-label="Message CineSense"
          placeholder="e.g. “like Interstellar, but shorter”"
          disabled={!live}
          maxLength={1000}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" aria-label="Send" disabled={!live || busy}>
          ➤
        </button>
      </form>
      {!live && <p className="chat-hint">The chat agent is coming soon</p>}
      <div className="chat-chips">
        {quick.map((q) => (
          <button key={q.label} type="button" aria-pressed={q.on} className={q.on ? "is-on" : ""} disabled={busy} onClick={q.toggle}>
            {q.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Minimal formatting for agent replies: paragraphs, line breaks and **bold** titles; no HTML injection. */
function Reply({ text }: { text: string }) {
  return (
    <>
      {text.split(/\n{2,}/).map((para, i) => (
        <p key={i}>
          {para.split("\n").map((line, j) => (
            <span key={j} className="chat-line">
              {line.split(/(\*\*[^*]+\*\*)/).map((part, k) =>
                part.startsWith("**") && part.endsWith("**") ? <strong key={k}>{part.slice(2, -2)}</strong> : part,
              )}
            </span>
          ))}
        </p>
      ))}
    </>
  );
}

"use client";

import { useSyncExternalStore } from "react";
import { type Criteria, emptyCriteria } from "@/lib/searchState";
import type { RankedMovie } from "@/lib/types";
import { randomId, userHeaders } from "@/lib/user";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const UNAVAILABLE = "The assistant is unavailable right now — you can still use the chips and search.";

export type Proposal = { idx: number; tag: string; mode: "not" };
export type Handoff = { world_id: string; film_id: string };
export type ChatFinal = {
  reply: string;
  criteria: Criteria;
  results: RankedMovie[];
  picks?: number; // how many results the reply presents (3-5)
  proposals: Proposal[];
  handoff: Handoff | null;
  usage: Record<string, number>;
};
export type ChatEntry =
  | { role: "user"; text: string }
  | {
      role: "bot";
      text: string;
      results?: RankedMovie[];
      picks?: number;
      criteria?: Criteria; // what this reply set: its picks count only while the search is unchanged
      proposals?: Proposal[];
      handoff?: Handoff | null;
      error?: boolean;
    };

/** Whether a reply's search is still the one set now (the world never matters; edited settings make it another). */
export function sameSearch(a: Criteria, b: Criteria): boolean {
  return JSON.stringify({ ...emptyCriteria(), ...a, world_id: null }) === JSON.stringify({ ...emptyCriteria(), ...b, world_id: null });
}

/** The films a reply presents: its first `picks` results (3 when an older reply doesn't say). */
export function replyPicks(e: ChatEntry): RankedMovie[] {
  return e.role === "bot" && e.results ? e.results.slice(0, e.picks ?? 3) : [];
}

export class ChatError extends Error {}

type SSEEvent = { event: string; data: { text?: string } & Partial<ChatFinal> };

/** Splits a buffer into complete SSE events and the incomplete remainder. */
export function parseSSE(buffer: string): [SSEEvent[], string] {
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events = blocks
    .map((b) => {
      const lines = Object.fromEntries(b.split("\n").map((l) => [l.slice(0, l.indexOf(": ")), l.slice(l.indexOf(": ") + 2)]));
      return lines.event && lines.data ? { event: lines.event, data: JSON.parse(lines.data) } : null;
    })
    .filter((e): e is SSEEvent => e !== null);
  return [events, rest];
}

/** One chat turn against POST /api/chat (Server-Sent Events). Rejects with ChatError(text). */
export async function streamChat(
  req: { threadId: string; message: string; criteria: Criteria },
  onStatus: (text: string) => void,
): Promise<ChatFinal> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...userHeaders() },
      body: JSON.stringify({ thread_id: req.threadId, message: req.message, criteria: req.criteria }),
    });
  } catch {
    throw new ChatError(UNAVAILABLE);
  }
  if (!res.ok || !res.body) throw new ChatError(UNAVAILABLE);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    const [events, rest] = parseSSE(buffer);
    buffer = rest;
    for (const e of events) {
      if (e.event === "status" && e.data.text) onStatus(e.data.text);
      if (e.event === "final") return e.data as ChatFinal;
      if (e.event === "error") throw new ChatError(e.data.text ?? UNAVAILABLE);
    }
    if (done) throw new ChatError(UNAVAILABLE);
  }
}

const THREAD_KEY = "cinesense.thread";
let memoryThread: string | null = null;

/** One conversation per browser tab (sessionStorage); homepage and genre drawer share it. */
export function threadId(): string {
  try {
    const existing = window.sessionStorage.getItem(THREAD_KEY);
    if (existing) return existing;
    const id = randomId();
    window.sessionStorage.setItem(THREAD_KEY, id);
    return id;
  } catch {
    memoryThread ??= randomId();
    return memoryThread;
  }
}

// --- conversation log shared across pages ---------------------------------------
const LOG_KEY = "cinesense.chat";
let log: ChatEntry[] | null = null;
const listeners = new Set<() => void>();
const EMPTY: ChatEntry[] = [];

function loadLog(): ChatEntry[] {
  if (log) return log;
  try {
    log = JSON.parse(window.sessionStorage.getItem(LOG_KEY) ?? "[]") as ChatEntry[];
  } catch {
    log = [];
  }
  return log;
}

export function setChatLog(next: ChatEntry[]) {
  log = next;
  try {
    window.sessionStorage.setItem(LOG_KEY, JSON.stringify(next));
  } catch {
    /* memory only */
  }
  listeners.forEach((l) => l());
}

export function getChatLog(): ChatEntry[] {
  return loadLog();
}

export function clearChatLog() {
  status = null;
  setChatLog([]);
}

/** "Start over": an empty log and a new thread, so the agent forgets the conversation as well. */
export function resetConversation() {
  try {
    window.sessionStorage.removeItem(THREAD_KEY);
  } catch {
    /* memory only */
  }
  memoryThread = null;
  clearChatLog();
}

// --- turn in flight, shared so a second panel (genre drawer) shows it and can't start another turn ---
let status: string | null = null;

export function setChatStatus(next: string | null) {
  status = next;
  listeners.forEach((l) => l());
}

export function useChatStatus(): string | null {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => status,
    () => null,
  );
}

export function useChatLog(): [ChatEntry[], (next: ChatEntry[]) => void] {
  const value = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    loadLog,
    () => EMPTY,
  );
  return [value, setChatLog];
}

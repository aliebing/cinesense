"use client";

import { useSyncExternalStore } from "react";
import type { Criteria } from "@/lib/searchState";
import type { RankedMovie } from "@/lib/types";
import { USER_HEADER, userId } from "@/lib/user";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const UNAVAILABLE = "The assistant is unavailable right now — you can still use the chips and search.";

export type Proposal = { idx: number; tag: string; mode: "not" };
export type Handoff = { world_id: string; film_id: string };
export type ChatFinal = {
  reply: string;
  criteria: Criteria;
  results: RankedMovie[];
  proposals: Proposal[];
  handoff: Handoff | null;
  usage: Record<string, number>;
};
export type ChatEntry =
  | { role: "user"; text: string }
  | { role: "bot"; text: string; results?: RankedMovie[]; proposals?: Proposal[]; handoff?: Handoff | null; error?: boolean };

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
      headers: { "Content-Type": "application/json", [USER_HEADER]: userId() },
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
    const id = crypto.randomUUID();
    window.sessionStorage.setItem(THREAD_KEY, id);
    return id;
  } catch {
    memoryThread ??= crypto.randomUUID();
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

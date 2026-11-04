import { afterEach, expect, it, vi } from "vitest";
import { ChatError, parseSSE, streamChat, threadId } from "@/lib/chat";
import { emptyCriteria } from "@/lib/searchState";

function sseResponse(chunks: string[]) {
  const enc = new TextEncoder();
  const body = new ReadableStream({
    start(c) {
      chunks.forEach((s) => c.enqueue(enc.encode(s)));
      c.close();
    },
  });
  return new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } });
}

afterEach(() => vi.restoreAllMocks());

it("parses complete events and keeps the remainder", () => {
  const [events, rest] = parseSSE('event: status\ndata: {"text":"a"}\n\nevent: fi');
  expect(events).toEqual([{ event: "status", data: { text: "a" } }]);
  expect(rest).toBe("event: fi");
});

it("streams status lines and resolves with the final payload, even when split across chunks", async () => {
  const final = { reply: "hi", criteria: emptyCriteria(), results: [], proposals: [], handoff: null, usage: {} };
  const payload = `event: status\ndata: {"text":"Searching plots…"}\n\nevent: final\ndata: ${JSON.stringify(final)}\n\n`;
  vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse([payload.slice(0, 30), payload.slice(30)]));
  const status: string[] = [];
  const out = await streamChat({ threadId: "t", message: "m", criteria: emptyCriteria() }, (s) => status.push(s));
  expect(status).toEqual(["Searching plots…"]);
  expect(out.reply).toBe("hi");
});

it("rejects with the server's error text", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse(['event: error\ndata: {"text":"unavailable"}\n\n']));
  await expect(streamChat({ threadId: "t", message: "m", criteria: emptyCriteria() }, () => {})).rejects.toEqual(
    new ChatError("unavailable"),
  );
});

it("reuses the thread id within the session", () => {
  const a = threadId();
  expect(a).toMatch(/[0-9a-f-]{36}/);
  expect(threadId()).toBe(a);
});

import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
  window.localStorage.clear();
});

it("creates an id without crypto.randomUUID (plain http on a LAN address)", async () => {
  vi.stubGlobal("crypto", { getRandomValues: (a: Uint8Array) => a.fill(7) });
  const { ensureUserId, userId } = await import("@/lib/user");
  const id = ensureUserId();
  expect(id).toMatch(/^[0-9a-f-]{36}$/);
  expect(userId()).toBe(id);
  expect(ensureUserId()).toBe(id);
});

it("reading the id never creates one, so a visitor without ratings sends no header", async () => {
  const { userHeaders, userId } = await import("@/lib/user");
  expect(userId()).toBe("");
  expect(userHeaders()).toEqual({});
  expect(window.localStorage.getItem("cinesense.user")).toBeNull();
});

it("the first rating creates the id and later requests carry it", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  const { apiGet, sendFeedback } = await import("@/lib/api");
  await apiGet("/api/home");
  expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty("X-CineSense-User");
  await sendFeedback("Q1", 1);
  const id = window.localStorage.getItem("cinesense.user");
  expect(id).toMatch(/^[0-9a-f-]{36}$/);
  expect(fetchMock.mock.calls[1][1].headers["X-CineSense-User"]).toBe(id);
});
